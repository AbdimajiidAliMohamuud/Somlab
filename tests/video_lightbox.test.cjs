const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname, "../static/js/site.js"), "utf8");

function classes(initial = []) {
  const values = new Set(initial);
  return {
    contains: (value) => values.has(value),
    toggle: (value, force) => force ? values.add(value) : values.delete(value),
  };
}

function button() {
  const listeners = {};
  return {
    hidden: true,
    classList: classes(),
    addEventListener: (name, callback) => { listeners[name] = callback; },
    setAttribute: () => {},
    focus: () => {},
    click: () => listeners.click(),
  };
}

function source(src = "", dataSrc = "/video/source") {
  return {
    src,
    type: "video/mp4",
    dataset: { src: dataSrc },
    getAttribute(name) { return this[name] || ""; },
    removeAttribute(name) { this[name] = ""; },
    addEventListener: () => {},
  };
}

function video(videoSource = source()) {
  const listeners = {};
  return {
    source: videoSource,
    listeners,
    muted: true,
    loop: true,
    poster: "/poster.jpg",
    isConnected: true,
    playCount: 0,
    pauseCount: 0,
    fullscreenCount: 0,
    readyState: 0,
    querySelector: () => videoSource,
    addEventListener: (name, callback) => { listeners[name] = callback; },
    removeAttribute(name) { this[name] = ""; },
    load: () => {},
    pause() { this.pauseCount += 1; },
    play() { this.playCount += 1; return Promise.resolve(); },
    requestFullscreen() { this.fullscreenCount += 1; return Promise.resolve(); },
  };
}

function runSiteJs(surfaces, width, observe = false) {
  const modalVideo = video(source("", ""));
  const modalClose = button();
  const modalFullscreen = button();
  const listeners = {};
  const dialog = {
    open: false,
    querySelector: (selector) => ({
      "[data-video-lightbox-player]": modalVideo,
      "[data-video-lightbox-source]": modalVideo.source,
      "[data-video-lightbox-close]": modalClose,
      "[data-video-lightbox-fullscreen]": modalFullscreen,
    })[selector],
    addEventListener: (name, callback) => { listeners[name] = callback; },
    showModal() { this.open = true; },
    close() { this.open = false; listeners.close(); },
  };
  const document = {
    hidden: false,
    querySelector: (selector) => selector === "[data-video-lightbox]" ? dialog : null,
    getElementById: () => null,
    querySelectorAll: (selector) => surfaces[selector] || [],
    addEventListener: () => {},
  };
  const observers = [];
  const window = { innerWidth: width };
  const IntersectionObserver = class {
    constructor(callback) { observers.push(callback); }
    observe() {}
  };
  if (observe) window.IntersectionObserver = IntersectionObserver;
  vm.runInNewContext(script, { document, window, IntersectionObserver, console });
  return {
    dialog, modalVideo, modalClose, modalFullscreen,
    notifyVisibility: (isIntersecting) => observers.forEach((callback) => callback([{ isIntersecting }])),
  };
}

test("closing after a customer card leaves view does not restart its preview", () => {
  const preview = video();
  const play = button();
  const player = {
    classList: classes(),
    querySelector: (selector) => ({
      video: preview,
      "[data-customer-video-play]": play,
      "[data-customer-video-error]": { hidden: true },
      "[data-customer-video-fullscreen]": button(),
      "[data-customer-video-retry]": button(),
    })[selector],
  };
  const lightbox = runSiteJs({ "[data-customer-video-player]": [player] }, 375, true);
  lightbox.notifyVisibility(true);
  assert.equal(preview.playCount, 1);
  play.click();
  lightbox.notifyVisibility(false);
  lightbox.modalClose.click();
  assert.equal(preview.playCount, 1);
  assert.equal(preview.muted, true);
});

for (const width of [1280, 375]) {
  test(`customer card and fullscreen icon open an audible modal at ${width}px`, () => {
    const preview = video();
    const play = button();
    const fullscreen = button();
    const retry = button();
    const error = { hidden: true };
    const player = {
      classList: classes(),
      querySelector: (selector) => ({
        video: preview,
        "[data-customer-video-play]": play,
        "[data-customer-video-error]": error,
        "[data-customer-video-fullscreen]": fullscreen,
        "[data-customer-video-retry]": retry,
      })[selector],
    };
    const lightbox = runSiteJs({ "[data-customer-video-player]": [player] }, width);

    assert.equal(preview.playCount, 1, "muted card preview starts");
    assert.equal(preview.muted, true);
    preview.listeners.error();
    assert.equal(play.hidden, false, "a preview error must not block opening the viewer");
    preview.listeners.play();
    assert.equal(play.hidden, false);
    play.click();
    assert.equal(lightbox.dialog.open, true);
    assert.equal(preview.pauseCount, 1);
    assert.equal(lightbox.modalVideo.source.src, preview.source.dataset.src);
    assert.equal(lightbox.modalVideo.muted, false);
    assert.equal(lightbox.modalVideo.volume, 1);
    assert.equal(lightbox.modalVideo.controls, true);
    assert.equal(lightbox.modalVideo.playCount, 1);
    lightbox.modalClose.click();
    assert.equal(lightbox.dialog.open, false);
    assert.equal(lightbox.modalVideo.pauseCount, 1);
    assert.equal(lightbox.modalVideo.source.src, "");
    assert.equal(preview.muted, true);
    assert.equal(preview.playCount, 2, "preview resumes after close");

    fullscreen.click();
    assert.equal(lightbox.dialog.open, true);
    assert.equal(preview.fullscreenCount, 0, "card icon opens the viewer, not fullscreen");
    lightbox.modalFullscreen.click();
    assert.equal(lightbox.modalVideo.fullscreenCount, 1);
  });

  test(`product card and thumbnail open the same modal at ${width}px`, () => {
    const preview = video();
    const openButton = button();
    const fullscreenButton = button();
    const thumbnail = button();
    const slide = {
      hidden: false,
      classList: classes(["is-active"]),
      querySelector: (selector) => ({
        video: preview,
        "[data-product-video-open]": openButton,
        "[data-product-video-fullscreen]": fullscreenButton,
      })[selector] || preview.source,
    };
    const gallery = {
      querySelectorAll: (selector) => selector === "[data-gallery-slide]" ? [slide] : [thumbnail],
    };
    const lightbox = runSiteJs({ "[data-product-gallery]": [gallery] }, width);

    assert.equal(preview.playCount, 1, "muted card preview starts");
    openButton.click();
    assert.equal(lightbox.dialog.open, true);
    assert.equal(preview.pauseCount, 1);
    assert.equal(lightbox.modalVideo.muted, false);
    lightbox.modalClose.click();
    assert.equal(preview.playCount, 2);

    fullscreenButton.click();
    assert.equal(lightbox.dialog.open, true);
    lightbox.modalClose.click();
    thumbnail.click();
    assert.equal(lightbox.dialog.open, true);
    assert.equal(preview.fullscreenCount, 0);
  });
}
