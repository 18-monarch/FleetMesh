'use strict';
// Read-only entry points from the cinematic introduction. Navigation never starts a run.
window.addEventListener('DOMContentLoaded', () => {
  const destination = window.location.hash;
  if (destination === '#sample') openReplay('sample');
  else if (destination === '#evidence') setView('evidence');
  else if (destination === '#review') loadReview('sample');
});
