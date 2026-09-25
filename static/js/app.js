const CIAS = {
  async api(url, options = {}) {
    const init = { method: options.method || "GET", headers: {} };
    if (options.body) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    const res = await fetch(url, init);
    try {
      return await res.json();
    } catch (err) {
      return { ok: false, error: "Unexpected server response." };
    }
  },

  toast(message, type = "success") {
    const host = document.getElementById("toast-host") || document.querySelector(".toasts") || document.querySelector(".content") || document.body;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span></span><button type="button" class="toast-x" data-dismiss-toast aria-label="Close">×</button>`;
    el.querySelector("span").textContent = message;
    host.prepend(el);
    setTimeout(() => el.remove(), 5000);
  },

  table(headers, rows) {
    if (!rows.length) {
      return `<p class="muted">No records yet.</p>`;
    }
    return `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((cols) => `<tr>${cols.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  },

  formData(form) {
    const data = {};
    new FormData(form).forEach((value, key) => {
      const field = form.elements[key];
      data[key] = field && field.type === "checkbox" ? field.checked : value;
    });
    return data;
  },

  openModal(title, html, onSubmit) {
    const modal = document.getElementById("modal");
    document.getElementById("modal-title").textContent = title;
    const form = document.getElementById("modal-form");
    form.innerHTML = html;
    modal.hidden = false;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const data = CIAS.formData(form);
      data._add_more = !!(e.submitter && e.submitter.hasAttribute("data-add-more"));
      await onSubmit(data);
    };
  },

  closeModal() {
    document.getElementById("modal").hidden = true;
  },

  async loadFloors(buildingId, selectEl, selected) {
    const res = await CIAS.api("/api/floors" + (buildingId ? `?building_id=${buildingId}` : ""));
    const floors = res.data || [];
    selectEl.innerHTML = `<option value="">Any floor</option>` +
      floors.map((f) => `<option value="${f.id}" ${String(f.id) === String(selected) ? "selected" : ""}>${f.name}</option>`).join("");
  },

  quickBook(room, filters) {
    const params = new URLSearchParams({
      classroom_id: room.id,
      day: filters.day,
    });
    window.location.href = "/bookings?" + params.toString();
  },
};

document.addEventListener("click", (e) => {
  if (e.target.matches("[data-close]") || e.target.id === "modal") {
    CIAS.closeModal();
  }
  if (e.target.closest("[data-dismiss-toast]")) {
    const toast = e.target.closest(".toast");
    if (toast) toast.remove();
  }
});
