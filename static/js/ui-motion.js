(() => {
  const F = (window.Fantareal = window.Fantareal || {});
  const Motion = (F.motion = F.motion || {});
  const reduceQuery = "(prefers-reduced-motion: reduce)";
  const disclosureCleanups = new WeakMap();

  function prefersReducedMotion() {
    return Boolean(window.matchMedia?.(reduceQuery)?.matches);
  }

  function nextFrame(callback) {
    return requestAnimationFrame(() => requestAnimationFrame(callback));
  }

  function parseTimeList(value) {
    return String(value || "")
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        if (part.endsWith("ms")) return Number.parseFloat(part);
        if (part.endsWith("s")) return Number.parseFloat(part) * 1000;
        return Number.parseFloat(part) || 0;
      });
  }

  function getMaxMotionTime(element) {
    if (!element || !window.getComputedStyle) return 0;
    const style = window.getComputedStyle(element);
    const transitionDurations = parseTimeList(style.transitionDuration);
    const transitionDelays = parseTimeList(style.transitionDelay);
    const animationDurations = parseTimeList(style.animationDuration);
    const animationDelays = parseTimeList(style.animationDelay);
    const transitionMax = transitionDurations.reduce((max, duration, index) => {
      return Math.max(max, duration + (transitionDelays[index] ?? transitionDelays[0] ?? 0));
    }, 0);
    const animationMax = animationDurations.reduce((max, duration, index) => {
      return Math.max(max, duration + (animationDelays[index] ?? animationDelays[0] ?? 0));
    }, 0);
    return Math.max(transitionMax, animationMax);
  }

  function afterMotion(element, callback, fallbackMs) {
    if (!element || typeof callback !== "function") return () => {};
    if (prefersReducedMotion()) {
      callback();
      return () => {};
    }

    let done = false;
    let timer = 0;
    const startedAt = performance.now();
    const finishOnMotionEnd = (event) => {
      if (event?.target && event.target !== element) return;
      const elapsed = performance.now() - startedAt;
      if (elapsed >= delay - 24) finish();
    };
    const finish = (event) => {
      if (event?.target && event.target !== element) return;
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      element.removeEventListener("transitionend", finish);
      element.removeEventListener("transitionend", finishOnMotionEnd);
      element.removeEventListener("animationend", finishOnMotionEnd);
      callback();
    };

    const delay = Number.isFinite(fallbackMs)
      ? fallbackMs
      : getMaxMotionTime(element) + 40;

    element.addEventListener("transitionend", finishOnMotionEnd);
    element.addEventListener("animationend", finishOnMotionEnd);
    timer = window.setTimeout(finish, Math.max(delay, 40));

    return () => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      element.removeEventListener("transitionend", finish);
      element.removeEventListener("transitionend", finishOnMotionEnd);
      element.removeEventListener("animationend", finishOnMotionEnd);
    };
  }

  function withMotionClass(element, className, options = {}) {
    if (!element || !className) return Promise.resolve(false);
    const { restart = true, doneClass, fallbackMs } = options;

    if (prefersReducedMotion()) {
      if (doneClass) element.classList.add(doneClass);
      return Promise.resolve(false);
    }

    if (restart) {
      element.classList.remove(className);
      void element.offsetWidth;
    }

    element.classList.add(className);

    return new Promise((resolve) => {
      afterMotion(element, () => {
        element.classList.remove(className);
        if (doneClass) element.classList.add(doneClass);
        resolve(true);
      }, fallbackMs);
    });
  }

  function normalizeBoolean(value) {
    return value === true || value === "true";
  }

  function setDisclosureHidden(body, collapsed, mode = "auto") {
    if (!body) return;
    const shouldHide = normalizeBoolean(collapsed);
    body.setAttribute("aria-hidden", shouldHide ? "true" : "false");

    if (mode === "display" || mode === "auto") {
      body.style.display = shouldHide ? "none" : "";
    }

    if (mode === "hidden" || mode === "auto") {
      body.hidden = shouldHide;
    }
  }

  function applyDisclosureShellState(container, collapsed, options = {}) {
    if (!container) return;
    const isCollapsed = normalizeBoolean(collapsed);
    const { collapsedClass, dataAttribute = "collapsed", toggleData = true } = options;

    container.classList.toggle("is-disclosure-open", !isCollapsed);
    container.classList.toggle("is-disclosure-collapsed", isCollapsed);

    if (collapsedClass) {
      container.classList.toggle(collapsedClass, isCollapsed);
    }

    if (toggleData && dataAttribute) {
      container.dataset[dataAttribute] = isCollapsed ? "true" : "false";
    }
  }

  function clearDisclosureInlineStyles(body) {
    if (!body) return;
    body.style.height = "";
    body.style.overflow = "";
  }

  function clearDisclosureMotion(container, body) {
    if (body && disclosureCleanups.has(body)) {
      disclosureCleanups.get(body)?.();
      disclosureCleanups.delete(body);
    }

    container?.classList.remove("is-disclosure-opening", "is-disclosure-closing");
    body?.classList.remove("is-disclosure-entering", "is-disclosure-exiting");
    clearDisclosureInlineStyles(body);
  }

  function setDisclosureCollapsed(container, body, collapsed, options = {}) {
    if (!container || !body) return false;

    const {
      collapsedClass,
      dataAttribute = "collapsed",
      toggleData = true,
      hiddenMode = "auto",
      immediate,
      fallbackMs = 320,
    } = options;
    const isCollapsed = normalizeBoolean(collapsed);
    const wasReady = body.dataset.uiMotionReady === "true";
    const shouldAnimate = immediate === undefined
      ? wasReady && !prefersReducedMotion()
      : !immediate && !prefersReducedMotion();

    container.classList.add("ui-disclosure-card");
    body.classList.add("ui-disclosure-body");
    clearDisclosureMotion(container, body);

    if (!shouldAnimate) {
      applyDisclosureShellState(container, isCollapsed, { collapsedClass, dataAttribute, toggleData });
      setDisclosureHidden(body, isCollapsed, hiddenMode);
      body.dataset.uiMotionReady = "true";
      return false;
    }

    if (isCollapsed) {
      setDisclosureHidden(body, false, hiddenMode);
      applyDisclosureShellState(container, false, { collapsedClass, dataAttribute, toggleData });
      const startHeight = body.scrollHeight;
      body.style.height = `${startHeight}px`;
      body.style.overflow = "hidden";
      container.classList.add("is-disclosure-closing");
      body.classList.add("is-disclosure-exiting");
      nextFrame(() => {
        body.style.height = "0px";
      });
      const cleanup = afterMotion(body, () => {
        body.classList.remove("is-disclosure-exiting");
        container.classList.remove("is-disclosure-closing");
        clearDisclosureInlineStyles(body);
        applyDisclosureShellState(container, true, { collapsedClass, dataAttribute, toggleData });
        setDisclosureHidden(body, true, hiddenMode);
        disclosureCleanups.delete(body);
      }, fallbackMs);
      disclosureCleanups.set(body, cleanup);
      return true;
    }

    applyDisclosureShellState(container, false, { collapsedClass, dataAttribute, toggleData });
    setDisclosureHidden(body, false, hiddenMode);
    body.style.height = "0px";
    body.style.overflow = "hidden";
    container.classList.add("is-disclosure-opening");
    body.classList.add("is-disclosure-entering");
    nextFrame(() => {
      body.style.height = `${body.scrollHeight}px`;
    });
    const cleanup = afterMotion(body, () => {
      body.classList.remove("is-disclosure-entering");
      container.classList.remove("is-disclosure-opening");
      clearDisclosureInlineStyles(body);
      disclosureCleanups.delete(body);
    }, fallbackMs);
    disclosureCleanups.set(body, cleanup);
    return true;
  }

  function pulseItem(element, className = "ui-motion-item-pulse", options = {}) {
    return withMotionClass(element, className, {
      fallbackMs: 760,
      ...options,
    });
  }

  function removeWithMotion(element, options = {}) {
    if (!element) return Promise.resolve(false);
    const { className = "ui-motion-remove", fallbackMs = 260, beforeRemove } = options;

    if (typeof beforeRemove === "function") beforeRemove(element);

    if (prefersReducedMotion()) {
      element.remove();
      return Promise.resolve(false);
    }

    element.classList.add(className);
    return new Promise((resolve) => {
      afterMotion(element, () => {
        element.remove();
        resolve(true);
      }, fallbackMs);
    });
  }

  const DEFAULT_STATUS_CLASSES = [
    "is-idle",
    "is-busy",
    "is-loading",
    "is-saving",
    "is-success",
    "is-saved",
    "is-dirty",
    "is-error",
  ];

  function setStatusState(element, options = {}) {
    if (!element) return false;
    const {
      text,
      title,
      state,
      stateClass,
      stateClasses = DEFAULT_STATUS_CLASSES,
      pulseTarget,
      className = "ui-status-change",
      animate = true,
      dataState = true,
      fallbackMs = 620,
    } = options;

    if (text !== undefined) element.textContent = String(text ?? "");
    if (title !== undefined) element.title = String(title ?? "");

    if (Array.isArray(stateClasses) && stateClasses.length) {
      element.classList.remove(...stateClasses);
    }

    const nextClass = stateClass || (state ? `is-${state}` : "");
    if (nextClass) element.classList.add(nextClass);
    if (dataState && state) element.dataset.state = state;

    const target = pulseTarget || element;
    if (animate && target) {
      withMotionClass(target, className, { fallbackMs });
    }
    return true;
  }

  function pulseStatus(element, options = {}) {
    if (!element) return Promise.resolve(false);
    return withMotionClass(element, options.className || "ui-status-change", {
      fallbackMs: 620,
      ...options,
    });
  }

  Motion.prefersReducedMotion = prefersReducedMotion;
  Motion.nextFrame = nextFrame;
  Motion.getMaxMotionTime = getMaxMotionTime;
  Motion.afterMotion = afterMotion;
  Motion.afterTransition = afterMotion;
  Motion.withMotionClass = withMotionClass;
  Motion.setDisclosureCollapsed = setDisclosureCollapsed;
  Motion.setDisclosureHidden = setDisclosureHidden;
  Motion.pulseItem = pulseItem;
  Motion.removeWithMotion = removeWithMotion;
  Motion.setStatusState = setStatusState;
  Motion.pulseStatus = pulseStatus;
  window.FantarealMotion = Motion;
})();
