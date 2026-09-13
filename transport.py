"""Independent controllers with authenticated direct loopback UDP packets.

The physics supervisor exchanges observations and commanded velocities over
pipes. It does not route peer packets, choose paths or issue resource grants.
"""
import hashlib
import heapq
import hmac
import json
import multiprocessing as mp
import os
import random
import secrets
import socket
import time
import uuid
from agent import Agent
from simulation import World


def pack(message, secret):
    payload = json.dumps(message, sort_keys=True, separators=(',', ':')).encode()
    signature = hmac.new(secret, payload, hashlib.sha256).hexdigest().encode()
    return signature+b'\n'+payload


def unpack(raw, secret):
    signature, payload = raw.split(b'\n', 1)
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest().encode()
    if not hmac.compare_digest(signature, expected):
        raise ValueError('Invalid message authentication')
    return json.loads(payload)


def worker(rid, config, model, pipe, secret):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 0)); sock.setblocking(False)
    pipe.send(sock.getsockname())
    peers = pipe.recv()
    agent = Agent(rid, config, model)
    rng = random.Random(config['seed']+rid+724)
    pending, seq, cursor = [], 0, 0
    stats = {'sent': 0, 'received': 0, 'lost': 0, 'rejected': 0}
    try:
        while True:
            obs = pipe.recv()
            if obs is None:
                break
            inbox = []
            while True:
                try:
                    raw, address = sock.recvfrom(65535)
                    if address not in peers:
                        stats['rejected'] += 1; continue
                    message = unpack(raw, secret)
                    if message.get('sender') != peers.index(address):
                        stats['rejected'] += 1; continue
                    if not obs['partitioned']:
                        inbox.append(message); stats['received'] += 1
                except BlockingIOError:
                    break
                except (ValueError, KeyError, TypeError):
                    stats['rejected'] += 1
            obs['messages'] = inbox
            started = time.perf_counter()
            result = agent.step(obs)
            elapsed = (time.perf_counter()-started)*1000
            for message in result.pop('messages'):
                for peer, address in enumerate(peers):
                    if peer == rid or message['to'] not in (None, peer):
                        continue
                    if obs['partitioned'] or rng.random() < config['drop']:
                        stats['lost'] += 1; continue
                    seq += 1
                    heapq.heappush(pending, (obs['time']+rng.random()*config['delay'], seq, address, message))
            while pending and pending[0][0] <= obs['time']+1e-8:
                _, _, address, message = heapq.heappop(pending)
                if not obs['partitioned']:
                    sock.sendto(pack(message, secret), address); stats['sent'] += 1
            result['events'] = agent.events[cursor:]; cursor = len(agent.events)
            result['state'].update(pid=os.getpid(), step_ms=round(elapsed, 3), **stats)
            pipe.send(result)
    except (EOFError, BrokenPipeError, ConnectionResetError, KeyboardInterrupt):
        pass
    finally:
        sock.close(); pipe.close()


class ProcessRuntime:
    def __init__(self, config, model=None):
        self.config = dict(config, epoch=uuid.uuid4().hex)
        self.world = World(self.config)
        self.pipes, self.processes = [], []
        self.closed = False
        self.secret = secrets.token_bytes(32)
        context = mp.get_context('spawn')
        try:
            for rid in range(config['robots']):
                parent, child = context.Pipe()
                process = context.Process(target=worker, args=(rid, self.config, model, child, self.secret), daemon=True)
                process.start(); child.close()
                self.processes.append(process); self.pipes.append(parent)
            addresses = []
            for pipe in self.pipes:
                if not pipe.poll(10):
                    raise RuntimeError('A robot failed to start within 10 seconds')
                addresses.append(tuple(pipe.recv()))
            for pipe in self.pipes:
                pipe.send(addresses)
        except Exception:
            self.close()
            raise

    def step(self):
        w = self.world
        for rid, (process, pipe) in enumerate(zip(self.processes, self.pipes)):
            if rid in w.dead:
                continue
            if not process.is_alive():
                w.dead.add(rid); continue
            try:
                obs = w.observations(rid); obs['partitioned'] = w.partitioned
                pipe.send(obs)
            except (BrokenPipeError, EOFError, OSError):
                w.dead.add(rid)
        commands = []
        deadline = time.monotonic()+2
        for rid, pipe in enumerate(self.pipes):
            if rid not in w.dead and pipe.poll(max(0., deadline-time.monotonic())):
                try:
                    result = pipe.recv()
                    w.states[rid] = result['state']; w.job_views[rid] = result['jobs']
                    w.events.extend(result['events']); commands.append(result['velocity'])
                    continue
                except (EOFError, OSError):
                    pass
            if rid not in w.dead:
                self.kill(rid)
            w.states[rid]['reason'] = 'Process offline; simulated motor stopped'
            commands.append((0., 0.))
        w.apply(commands)
        return w.done()

    def kill(self, rid):
        process = self.processes[rid]
        if process.is_alive():
            process.terminate(); process.join(1)
        self.world.dead.add(rid)
        self.world.event('failure', f'R{rid+1} process stopped. Resource ownership has not expired.', rid)

    def close(self):
        if self.closed:
            return
        self.closed = True
        for pipe in self.pipes:
            try:
                pipe.send(None)
            except (BrokenPipeError, EOFError, OSError):
                pass
        for process in self.processes:
            process.join(.5)
            if process.is_alive():
                process.terminate(); process.join(1)
        for pipe in self.pipes:
            pipe.close()
