// Progressive enhancement for the server-rendered city pages (works with content injected later, too).
(function () {
  function beacon(kind, courseId) {
    if (!courseId) return;
    var body = JSON.stringify({ kind: kind, courseId: courseId });
    if (navigator.sendBeacon) navigator.sendBeacon("/api/insights/event", body);
    else fetch("/api/insights/event", { method: "POST", body: body, keepalive: true });
  }
  function courseOf(el) {
    var card = el.closest("[data-course]");
    return card && card.getAttribute("data-course");
  }

  document.addEventListener("change", function (e) {
    if (!e.target.matches("[data-autosubmit]")) return;
    var form = e.target.form;
    Array.prototype.forEach.call(form.querySelectorAll("select"), function (s) { if (!s.value) s.disabled = true; });
    form.submit();
  });

  document.addEventListener("toggle", function (e) {
    if (e.target.matches && e.target.matches("details[data-course]") && e.target.open) beacon("course_open", e.target.getAttribute("data-course"));
  }, true);

  document.addEventListener("click", function (e) {
    var tracked = e.target.closest("[data-track]");
    if (tracked) beacon(tracked.getAttribute("data-track"), courseOf(tracked));

    var share = e.target.closest("[data-share]");
    if (share) {
      var url = share.getAttribute("data-share");
      var status = share.nextElementSibling;
      beacon("share", courseOf(share));
      if (navigator.share) {
        navigator.share({ title: share.getAttribute("data-title"), url: url }).catch(function () {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(function () { if (status) status.textContent = share.getAttribute("data-copied"); });
      }
    }

    if (e.target.closest("[data-cookie-ok]")) {
      document.cookie = "cookie_ok=1; path=/; max-age=31536000; samesite=lax";
      var notice = document.querySelector("[data-cookie-notice]");
      if (notice) notice.remove();
    }
  });

  document.addEventListener("submit", function (e) {
    if (e.target.matches(".cs-controls")) {
      Array.prototype.forEach.call(e.target.querySelectorAll("select"), function (s) { if (!s.value) s.disabled = true; });
      return;
    }
    var form = e.target.closest("[data-remind]");
    if (!form) return;
    e.preventDefault();
    var status = form.querySelector(".cs-status");
    var button = form.querySelector("button");
    button.disabled = true;
    fetch("/api/reminders", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ courseId: form.courseId.value, email: form.email.value }),
    })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
      .then(function (res) {
        status.textContent = res.data.message || "";
        status.classList.toggle("cs-error", !res.ok);
      })
      .catch(function () { status.textContent = ""; })
      .finally(function () { button.disabled = false; });
  });

  function focusShared() {
    var open = document.querySelector("details[data-focus]");
    if (open) open.scrollIntoView({ block: "center" });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", focusShared);
  else focusShared();
  window.aolFocusShared = focusShared;
})();
