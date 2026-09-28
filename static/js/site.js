document.querySelector(".nav-toggle")?.addEventListener("click", (event) => {
  const nav = document.querySelector(".main-nav");
  const open = nav.classList.toggle("open");
  event.currentTarget.setAttribute("aria-expanded", open);
});

const productsNavigation = document.querySelector(".nav-products");
const productsToggle = productsNavigation?.querySelector(".nav-products-toggle");

if (productsNavigation && productsToggle) {
  const setProductsMenu = (open) => {
    productsNavigation.classList.toggle("open", open);
    productsToggle.setAttribute("aria-expanded", String(open));
  };

  productsToggle.addEventListener("click", () => {
    const desktopHover = window.matchMedia("(hover: hover) and (min-width: 1051px)").matches;
    setProductsMenu(desktopHover ? true : !productsNavigation.classList.contains("open"));
  });

  productsNavigation.addEventListener("mouseenter", () => {
    if (window.matchMedia("(hover: hover) and (min-width: 1051px)").matches) {
      setProductsMenu(true);
    }
  });

  productsNavigation.addEventListener("mouseleave", () => {
    if (
      window.matchMedia("(hover: hover) and (min-width: 1051px)").matches &&
      !productsNavigation.contains(document.activeElement)
    ) {
      setProductsMenu(false);
    }
  });

  productsNavigation.addEventListener("focusin", () => {
    if (window.matchMedia("(min-width: 1051px)").matches) {
      setProductsMenu(true);
    }
  });
  productsNavigation.addEventListener("focusout", () => {
    window.setTimeout(() => {
      if (!productsNavigation.contains(document.activeElement)) {
        setProductsMenu(false);
      }
    }, 0);
  });

  const closeProductsMenuFromOutside = (event) => {
    if (!productsNavigation.contains(event.target)) {
      setProductsMenu(false);
      productsToggle.blur();
    }
  };

  document.addEventListener("pointerdown", closeProductsMenuFromOutside);
  document.addEventListener("click", closeProductsMenuFromOutside);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && productsNavigation.classList.contains("open")) {
      setProductsMenu(false);
      productsToggle.focus();
    }
  });
}

document.querySelectorAll(".manufacturer-menu-toggle").forEach((button) => {
  const submenu = document.getElementById(button.getAttribute("aria-controls"));
  if (!submenu) return;

  const setNestedMenu = (open) => {
    button.setAttribute("aria-expanded", String(open));
    submenu.hidden = !open;
  };

  button.addEventListener("click", () => {
    setNestedMenu(button.getAttribute("aria-expanded") !== "true");
  });

  button.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && button.getAttribute("aria-expanded") === "true") {
      event.stopPropagation();
      setNestedMenu(false);
      button.focus();
    }
  });
});

const inquiryForm = document.querySelector("[data-product-inquiry-form]");
const inquiryProductData = document.getElementById("inquiry-products-by-group");

if (inquiryForm && inquiryProductData) {
  const groupSelect = inquiryForm.querySelector('[name="product_group"]');
  const productSelect = inquiryForm.querySelector('[name="product"]');

  if (groupSelect && productSelect) {
    const productsByGroup = JSON.parse(inquiryProductData.textContent);
    const renderProductOptions = () => {
      const previousProduct = productSelect.value;
      const products = productsByGroup[groupSelect.value] || [];
      productSelect.replaceChildren(new Option("Select a product", ""));
      products.forEach((product) => {
        productSelect.add(new Option(product.name, product.id));
      });
      if (products.some((product) => product.id === previousProduct)) {
        productSelect.value = previousProduct;
      }
    };

    groupSelect.addEventListener("change", renderProductOptions);
  }
}

document.querySelector(".dash-menu")?.addEventListener("click", () => {
  document.querySelector(".dash-sidebar")?.classList.toggle("open");
});

document.querySelectorAll(".alert button").forEach((button) => {
  button.addEventListener("click", () => button.parentElement.remove());
});

const heroSlider = document.querySelector("[data-hero-slider]");
if (heroSlider) {
  const slides = [...heroSlider.querySelectorAll(".hero-slide")];
  let activeSlide = 0;

  if (slides.length > 1) {
    window.setInterval(() => {
      const nextSlide = (activeSlide + 1) % slides.length;
      slides[activeSlide].classList.remove("is-active");
      slides[activeSlide].setAttribute("aria-hidden", "true");
      slides[nextSlide].classList.add("is-active");
      slides[nextSlide].removeAttribute("aria-hidden");
      activeSlide = nextSlide;
    }, 4500);
  }
}

document.querySelectorAll("[data-manufacturer-logo]").forEach((image) => {
  const showFallback = () => {
    const card = image.closest(".manufacturer-logo-card");
    const visual = image.closest(".manufacturer-logo-visual");
    const fallback = card?.querySelector(".manufacturer-logo-fallback");
    if (visual) {
      visual.hidden = true;
    } else {
      image.hidden = true;
    }
    if (fallback) {
      fallback.hidden = false;
    }
  };

  image.addEventListener("error", showFallback, { once: true });
  if (image.complete && image.naturalWidth === 0) {
    showFallback();
  }
});

document.querySelectorAll("[data-counter]").forEach((counter) => {
  const target = Number(counter.dataset.counterTarget);
  if (!Number.isFinite(target)) {
    return;
  }

  const showFinalValue = () => {
    counter.textContent = String(target);
  };
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion || !("IntersectionObserver" in window)) {
    showFinalValue();
    return;
  }

  counter.textContent = "0";
  let hasAnimated = false;
  const observer = new IntersectionObserver((entries) => {
    if (hasAnimated || !entries.some((entry) => entry.isIntersecting)) {
      return;
    }
    hasAnimated = true;
    observer.disconnect();
    const startedAt = performance.now();
    const duration = 1000;

    const updateCounter = (now) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      counter.textContent = String(Math.round(target * easedProgress));
      if (progress < 1) {
        window.requestAnimationFrame(updateCounter);
      } else {
        showFinalValue();
      }
    };

    window.requestAnimationFrame(updateCounter);
  }, { threshold: 0.35 });
  observer.observe(counter);
});

const customerLightbox = document.querySelector("[data-customer-lightbox-dialog]");
if (customerLightbox) {
  const lightboxImage = customerLightbox.querySelector("[data-customer-lightbox-image]");
  const lightboxCaption = customerLightbox.querySelector("[data-customer-lightbox-caption]");
  const closeButton = customerLightbox.querySelector("[data-customer-lightbox-close]");
  let opener;

  const closeCustomerLightbox = () => {
    customerLightbox.close();
    opener?.focus();
  };

  document.querySelectorAll("[data-customer-lightbox]").forEach((button) => {
    button.addEventListener("click", () => {
      opener = button;
      lightboxImage.src = button.dataset.imageSrc;
      lightboxImage.alt = button.dataset.imageAlt || "Customer project image";
      lightboxCaption.textContent = button.dataset.imageCaption || "";
      lightboxCaption.hidden = !lightboxCaption.textContent;
      customerLightbox.showModal();
      closeButton.focus();
    });
  });

  closeButton.addEventListener("click", closeCustomerLightbox);
  customerLightbox.addEventListener("click", (event) => {
    if (event.target === customerLightbox) closeCustomerLightbox();
  });
}

document.querySelectorAll("[data-customer-video-limit]").forEach((input) => {
  input.addEventListener("change", () => {
    const oversized = Array.from(input.files || []).find((file) =>
      /\.(mp4|webm|mov|m4v|ogv|ogg)$/i.test(file.name)
      && file.size > Number(input.dataset.customerVideoLimit));
    input.setCustomValidity(oversized ? "Each video must be under 1 GB (maximum 999,999,999 bytes)." : "");
    if (oversized) input.reportValidity();
  });
  input.form?.addEventListener("submit", () => {
    if (input.files?.length && input.checkValidity()) {
      const submit = input.form.querySelector('[type="submit"], button.btn-primary');
      if (submit) submit.textContent = "Uploading and preparing video…";
    }
  });
});

document.querySelectorAll("[data-customer-video-player]").forEach((player) => {
  const video = player.querySelector("video");
  const play = player.querySelector("[data-customer-video-play]");
  const error = player.querySelector("[data-customer-video-error]");
  const fullscreen = player.querySelector("[data-customer-video-fullscreen]");
  fullscreen.hidden = false;
  const setFullscreenLabel = () => fullscreen.setAttribute("aria-label",
    player.classList.contains("is-fullscreen-fallback") || document.fullscreenElement === video
      ? "Exit video fullscreen" : "Enter video fullscreen");
  const closeFallbackFullscreen = () => {
    player.classList.remove("is-fullscreen-fallback");
    player.removeAttribute("role");
    player.removeAttribute("aria-modal");
    setFullscreenLabel();
  };
  const openFallbackFullscreen = () => {
    player.classList.add("is-fullscreen-fallback");
    player.setAttribute("role", "dialog");
    player.setAttribute("aria-modal", "true");
    setFullscreenLabel();
  };
  fullscreen.addEventListener("click", () => {
    if (player.classList.contains("is-fullscreen-fallback")) {
      closeFallbackFullscreen();
    } else if (document.fullscreenElement === video) {
      document.exitFullscreen?.();
    } else if (video.requestFullscreen) {
      video.requestFullscreen().then(setFullscreenLabel).catch(openFallbackFullscreen);
    } else if (video.webkitEnterFullscreen) {
      video.webkitEnterFullscreen();
    } else {
      openFallbackFullscreen();
    }
  });
  document.addEventListener("fullscreenchange", setFullscreenLabel);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && player.classList.contains("is-fullscreen-fallback"))
      closeFallbackFullscreen();
  });
  const fitVideo = () => player.classList.toggle("is-portrait", video.videoHeight > video.videoWidth);
  video.addEventListener("loadedmetadata", fitVideo);
  if (video.readyState >= 1) fitVideo();
  // Muted looping preview keeps one centered action; a click switches to normal playback.
  let isPreview = true;
  video.controls = false;
  play.hidden = false;
  const showError = () => { error.hidden = false; play.hidden = true; };
  const startWithAudio = () => {
    isPreview = false;
    error.hidden = true;
    video.loop = false;
    video.muted = false;
    video.controls = true;
    play.hidden = true;
    video.play().catch(showError);
  };
  play.addEventListener("click", startWithAudio);
  video.addEventListener("play", () => { if (!isPreview) play.hidden = true; error.hidden = true; });
  video.addEventListener("error", showError);
  // Source failures do not consistently bubble to the video element.
  video.querySelector("source").addEventListener("error", showError);
  video.play().catch(() => { /* The centered button remains available if autoplay is blocked. */ });
  player.querySelector("[data-customer-video-retry]").addEventListener("click", () => {
    video.load();
    startWithAudio();
  });
});

document.querySelectorAll("[data-quality-logo-carousel]").forEach((carousel) => {
  const logos = Array.from(carousel.querySelectorAll(".hero-partner-logo"));
  if (logos.length < 2) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let activeIndex = Math.max(0, logos.findIndex((logo) => logo.classList.contains("is-active")));
  let rotationTimer;

  const showLogo = (index) => {
    activeIndex = index;
    logos.forEach((logo, logoIndex) => {
      const isActive = logoIndex === activeIndex;
      logo.classList.toggle("is-active", isActive);
      if (isActive) {
        logo.removeAttribute("aria-hidden");
        logo.removeAttribute("tabindex");
      } else {
        logo.setAttribute("aria-hidden", "true");
        logo.setAttribute("tabindex", "-1");
      }
    });
  };

  const pauseRotation = () => window.clearTimeout(rotationTimer);
  const scheduleRotation = () => {
    pauseRotation();
    rotationTimer = window.setTimeout(() => {
      showLogo((activeIndex + 1) % logos.length);
      scheduleRotation();
    }, reducedMotion.matches ? 4000 : 3600);
  };

  showLogo(activeIndex);
  scheduleRotation();
  carousel.addEventListener("pointerenter", pauseRotation);
  carousel.addEventListener("pointerleave", scheduleRotation);
  carousel.addEventListener("focusin", pauseRotation);
  carousel.addEventListener("focusout", scheduleRotation);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pauseRotation();
    else scheduleRotation();
  });
  reducedMotion.addEventListener?.("change", scheduleRotation);
});

document.querySelectorAll("[data-smart-search]").forEach((search) => {
  const form = search.querySelector("form");
  const input = search.querySelector('input[name="q"]');
  const suggestions = search.querySelector(".search-suggestions");
  const endpoint = search.dataset.suggestionsUrl;
  let debounceTimer;
  let requestController;
  let activeIndex = -1;
  let suggestionLinks = [];

  const closeSuggestions = () => {
    suggestionLinks.forEach((link) => link.setAttribute("aria-selected", "false"));
    suggestions.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    activeIndex = -1;
    suggestionLinks = [];
  };

  const setActiveSuggestion = (index) => {
    suggestionLinks.forEach((link) => {
      link.classList.remove("is-active");
      link.setAttribute("aria-selected", "false");
    });
    if (!suggestionLinks.length) {
      activeIndex = -1;
      input.removeAttribute("aria-activedescendant");
      return;
    }
    activeIndex = (index + suggestionLinks.length) % suggestionLinks.length;
    const activeLink = suggestionLinks[activeIndex];
    activeLink.classList.add("is-active");
    activeLink.setAttribute("aria-selected", "true");
    input.setAttribute("aria-activedescendant", activeLink.id);
    activeLink.scrollIntoView({ block: "nearest" });
  };

  const renderSuggestions = (results) => {
    suggestions.replaceChildren();
    if (!results.length) {
      const empty = document.createElement("div");
      empty.className = "search-suggestion-empty";
      empty.setAttribute("role", "status");
      empty.textContent = "No matching products";
      suggestions.appendChild(empty);
      suggestionLinks = [];
    } else {
      suggestionLinks = results.map((product, index) => {
        const link = document.createElement("a");
        link.className = "search-suggestion";
        link.href = product.url;
        link.id = `product-suggestion-${index}`;
        link.setAttribute("role", "option");
        link.setAttribute("aria-selected", "false");

        const visual = document.createElement("span");
        visual.className = "search-suggestion-visual";
        if (product.thumbnail) {
          const image = document.createElement("img");
          image.src = product.thumbnail;
          image.alt = "";
          image.loading = "lazy";
          image.addEventListener("error", () => {
            image.remove();
            visual.textContent = product.category.slice(0, 2).toUpperCase();
          }, { once: true });
          visual.appendChild(image);
        } else {
          visual.textContent = product.category.slice(0, 2).toUpperCase();
        }

        const copy = document.createElement("span");
        copy.className = "search-suggestion-copy";
        const name = document.createElement("strong");
        name.className = "search-suggestion-name";
        name.textContent = product.name;
        const brand = document.createElement("span");
        brand.textContent = product.brand;
        copy.append(name, brand);

        const arrow = document.createElement("small");
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "→";
        link.append(visual, copy, arrow);
        suggestions.appendChild(link);
        return link;
      });
    }
    suggestions.hidden = false;
    input.setAttribute("aria-expanded", "true");
    activeIndex = -1;
    input.removeAttribute("aria-activedescendant");
  };

  const requestSuggestions = async (query) => {
    requestController?.abort();
    requestController = new AbortController();
    try {
      const response = await fetch(`${endpoint}?q=${encodeURIComponent(query)}`, {
        headers: { Accept: "application/json" },
        signal: requestController.signal,
      });
      if (!response.ok) {
        throw new Error(`Product suggestions returned ${response.status}`);
      }
      const payload = await response.json();
      if (input.value.trim() === query) {
        renderSuggestions(payload.results || []);
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        closeSuggestions();
      }
    }
  };

  input.addEventListener("input", () => {
    window.clearTimeout(debounceTimer);
    const query = input.value.trim();
    if (query.length < 2) {
      requestController?.abort();
      closeSuggestions();
      return;
    }
    debounceTimer = window.setTimeout(() => requestSuggestions(query), 250);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" && suggestionLinks.length) {
      event.preventDefault();
      setActiveSuggestion(activeIndex + 1);
    } else if (event.key === "ArrowUp" && suggestionLinks.length) {
      event.preventDefault();
      setActiveSuggestion(activeIndex - 1);
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      window.location.assign(suggestionLinks[activeIndex].href);
    } else if (event.key === "Enter") {
      event.preventDefault();
      form.requestSubmit();
    } else if (event.key === "Escape") {
      closeSuggestions();
    }
  });

  form.addEventListener("submit", () => requestController?.abort());
  document.addEventListener("pointerdown", (event) => {
    if (!search.contains(event.target)) {
      closeSuggestions();
    }
  });
  search.addEventListener("focusout", () => {
    window.setTimeout(() => {
      if (!search.contains(document.activeElement)) {
        closeSuggestions();
      }
    }, 0);
  });
});

document.querySelectorAll("img[data-image-fallback]").forEach((image) => {
  const showFallback = () => {
    const fallback = image.dataset.imageFallback;
    if (!fallback || image.dataset.fallbackApplied === "true") return;
    image.dataset.fallbackApplied = "true";
    image.src = fallback;
  };
  image.addEventListener("error", showFallback, { once: true });
  if (image.complete && image.naturalWidth === 0) showFallback();
});

const relatedPreviewTemplates = document.querySelectorAll("[data-product-related-preview]");
if (relatedPreviewTemplates.length) {
  const desktopHover = window.matchMedia(
    "(min-width: 1024px) and (hover: hover) and (pointer: fine)"
  );
  const preview = document.createElement("div");
  preview.className = "product-related-hover-preview";
  preview.setAttribute("aria-hidden", "true");
  preview.hidden = true;
  document.body.appendChild(preview);
  let hideTimer;

  const hideRelatedPreview = () => {
    window.clearTimeout(hideTimer);
    preview.classList.remove("is-visible");
    hideTimer = window.setTimeout(() => {
      if (!preview.classList.contains("is-visible")) {
        preview.hidden = true;
        preview.replaceChildren();
      }
    }, 150);
  };

  const positionRelatedPreview = (summary) => {
    if (preview.hidden) return;
    const summaryRect = summary.getBoundingClientRect();
    const previewRect = preview.getBoundingClientRect();
    const edge = 16;
    const gap = 10;
    const left = Math.min(
      Math.max(edge, summaryRect.right - previewRect.width),
      window.innerWidth - previewRect.width - edge
    );
    let top = summaryRect.bottom + gap;
    if (top + previewRect.height > window.innerHeight - edge) {
      top = summaryRect.top - previewRect.height - gap;
    }
    preview.style.left = `${left}px`;
    preview.style.top = `${Math.max(edge, top)}px`;
  };

  relatedPreviewTemplates.forEach((template) => {
    const item = template.closest(".product-related-item");
    const summary = item?.querySelector(":scope > summary");
    if (!item || !summary) return;

    summary.addEventListener("pointerenter", () => {
      if (!desktopHover.matches || item.open) return;
      window.clearTimeout(hideTimer);
      preview.replaceChildren(template.content.cloneNode(true));
      preview.hidden = false;
      positionRelatedPreview(summary);
      preview.querySelector("img")?.addEventListener(
        "load",
        () => positionRelatedPreview(summary),
        { once: true }
      );
      window.requestAnimationFrame(() => preview.classList.add("is-visible"));
    });
    summary.addEventListener("pointerleave", hideRelatedPreview);
    summary.addEventListener("click", hideRelatedPreview);
    item.addEventListener("toggle", () => {
      if (item.open) hideRelatedPreview();
    });
  });

  window.addEventListener("scroll", hideRelatedPreview, { passive: true });
  window.addEventListener("resize", hideRelatedPreview);
  desktopHover.addEventListener?.("change", hideRelatedPreview);
}

document.querySelectorAll("[data-product-gallery]").forEach((gallery) => {
  const slides = [...gallery.querySelectorAll("[data-gallery-slide]")];
  const thumbnails = [...gallery.querySelectorAll("[data-gallery-thumb]")];

  const showSlide = (index) => {
    slides.forEach((slide, slideIndex) => {
      const active = slideIndex === index;
      slide.hidden = !active;
      slide.classList.toggle("is-active", active);
      if (!active) {
        slide.querySelector("video")?.pause();
      }
    });
    thumbnails.forEach((thumbnail, thumbnailIndex) => {
      const active = thumbnailIndex === index;
      thumbnail.classList.toggle("is-active", active);
      thumbnail.setAttribute("aria-pressed", String(active));
    });
  };

  thumbnails.forEach((thumbnail, index) => {
    thumbnail.addEventListener("click", () => showSlide(index));
    thumbnail.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const nextIndex = (index + direction + thumbnails.length) % thumbnails.length;
      thumbnails[nextIndex].focus();
      showSlide(nextIndex);
    });
  });
});

document.querySelectorAll("[data-product-sections]").forEach((sectionGroup) => {
  const navigation = sectionGroup.querySelector("[data-product-section-nav]");
  const panelsWrapper = sectionGroup.querySelector(".product-section-panels");
  const links = [...sectionGroup.querySelectorAll("[data-product-section-link]")];
  const panels = [...sectionGroup.querySelectorAll("[data-product-section-panel]")];
  const panelById = new Map(panels.map((panel) => [panel.id, panel]));

  if (!navigation || !panelsWrapper || !links.length || !panels.length) return;

  navigation.setAttribute("role", "tablist");
  panelsWrapper.classList.add("is-enhanced");

  const activateSection = (panelId, updateHash = false) => {
    if (!panelById.has(panelId)) return;
    links.forEach((link) => {
      const active = link.getAttribute("href") === `#${panelId}`;
      link.classList.toggle("is-active", active);
      link.setAttribute("aria-selected", String(active));
      link.setAttribute("tabindex", active ? "0" : "-1");
    });
    panels.forEach((panel) => {
      panel.hidden = panel.id !== panelId;
    });
    if (updateHash && window.history?.replaceState) {
      window.history.replaceState(null, "", `#${panelId}`);
    }
  };

  links.forEach((link, index) => {
    const panelId = link.getAttribute("href").slice(1);
    link.id = `product-section-tab-${index}`;
    link.setAttribute("role", "tab");
    link.setAttribute("aria-controls", panelId);
    link.addEventListener("click", (event) => {
      event.preventDefault();
      activateSection(panelId, true);
    });
    link.addEventListener("keydown", (event) => {
      let nextIndex;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % links.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + links.length) % links.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = links.length - 1;
      if (nextIndex === undefined) return;
      event.preventDefault();
      links[nextIndex].focus();
      activateSection(links[nextIndex].getAttribute("href").slice(1), true);
    });
  });

  panels.forEach((panel, index) => {
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", links[index].id);
    panel.setAttribute("tabindex", "0");
  });

  const initialPanelId = panelById.has(window.location.hash.slice(1))
    ? window.location.hash.slice(1)
    : panels[0].id;
  activateSection(initialPanelId);

  window.addEventListener("hashchange", () => {
    activateSection(window.location.hash.slice(1));
  });
});

document.querySelectorAll('.manage-form-grid input[type="file"][accept*="image"]').forEach((input) => {
  const field = input.closest(".field");
  if (!field) return;
  let preview = field.querySelector(".admin-image-preview");
  let objectUrl = "";

  input.addEventListener("change", () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    const file = input.files?.[0];
    if (!file) return;
    objectUrl = URL.createObjectURL(file);
    if (!preview) {
      preview = document.createElement("div");
      preview.className = "admin-image-preview";
      preview.innerHTML = '<span>Selected image</span><img alt="Selected image preview">';
      input.insertAdjacentElement("afterend", preview);
    }
    preview.querySelector("span").textContent = "Selected image";
    const image = preview.querySelector("img");
    image.src = objectUrl;
    image.alt = `${file.name} preview`;
  });

  const clearInput = field.querySelector('input[type="checkbox"][name$="-clear"]');
  clearInput?.addEventListener("change", () => {
    if (preview) preview.hidden = clearInput.checked;
  });
});
