import '@testing-library/jest-dom/vitest';

// JSDOM scrollIntoView polyfill
if (typeof window !== 'undefined') {
  window.HTMLElement.prototype.scrollIntoView = function () {};
}
