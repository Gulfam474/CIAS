const CIASSetup = {
  state: { step: 1, data: null, lastBuildingId: "", lastFloorId: "" },

  init() {
    const root = document.getElementById("onboard");
    if (!root) return;
    this.root = root;
    this.panel = document.getElementById("step-panel");
    this.roomTypes = JSON.parse(root.dataset.roomTypes || "[]");
    this.searchUrl = root.dataset.searchUrl || "/search";
    this.state.step = Number(root.dataset.step || 1);
    root.querySelectorAll(".step").forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = Number(btn.dataset.goto);
        if (target <= this.maxAllowedStep()) this.goTo(target);
      });
    });
    this.refresh().then(() => this.goTo(this.state.step));
  },

  maxAllowedStep() {
    const c = (this.state.data && this.state.data.counts) || {};
    if (!c.buildings) return 1;
    if (!c.floors) return 2;
    if (!c.classrooms) return 3;
    return 4;
  },

  async refresh() {
    const res = await CIAS.api("/api/setup/status");
    if (!res.ok) {
      CIAS.toast(res.error, "error");
      return;
    }
    this.state.data = res.data;
    if (res.data.complete && this.state.step === 4) {
      this.closeAndReload();
      return true;
    }
    return false;
  },

  closeAndReload() {
    if (this.root) this.root.hidden = true;
    sessionStorage.setItem("cias_start_tour", "1");
    window.location.href = this.searchUrl || "/?tour=1";
  },

  paintStepper() {
    const allowed = this.maxAllowedStep();
    this.root.querySelectorAll(".step").forEach((btn) => {
      const n = Number(btn.dataset.goto);
      btn.classList.toggle("is-active", n === this.state.step);
      btn.classList.toggle(
        "is-done",
        n < this.state.step || (n < allowed && n !== this.state.step && this.countsFor(n))
      );
    });
  },

  countsFor(n) {
    const c = this.state.data.counts;
    return [c.buildings, c.floors, c.classrooms, c.timeslots][n - 1] > 0;
  },

  nextFloorNumber(buildingId) {
    const floors = (this.state.data.floors || []).filter((f) => String(f.building_id) === String(buildingId));
    if (!floors.length) return 1;
    return Math.max(...floors.map((f) => Number(f.floor_number) || 0)) + 1;
  },

  goTo(step) {
    this.state.step = step;
    this.paintStepper();
    const forms = [null, this.buildingForm, this.floorForm, this.classroomForm, this.slotForm];
    this.panel.innerHTML = forms[step].call(this);
    this.bindForm();
  },

  createdList(title, items) {
    if (!items.length) return "";
    return `<div class="created-box"><p>${title}</p><ul>${items}</ul></div>`;
  },

  stepActions(step, saveLabel, addMoreLabel) {
    const hasRows = this.countsFor(step);
    const finish = step === 4 && this.state.data.counts.timeslots > 0 && this.state.data.counts.classrooms > 0;
    return `<div class="setup-actions">
      ${step > 1 ? `<button class="btn" type="button" data-back>Back</button>` : ""}
      <button class="btn primary" type="submit">${saveLabel}</button>
      ${hasRows ? `<button class="btn" type="button" data-add-more>${addMoreLabel}</button>` : ""}
      ${hasRows && step < 4 ? `<button class="btn" type="button" data-next>Continue</button>` : ""}
      ${finish ? `<button class="btn" type="button" data-finish>Finish</button>` : ""}
    </div>`;
  },

  buildingForm() {
    const rows = (this.state.data.buildings || []).map((b) =>
      `<li><b>${b.name}</b> · ${b.code}${b.description ? `<div class="sub">${b.description}</div>` : ""}</li>`
    ).join("");
    return `
      <p class="eyebrow">Step 1 of 4</p>
      <h2>Add a college building</h2>
      <p class="muted">You can add more than one building. Use Continue when this step is done.</p>
      <form id="setup-form" class="stack setup-form">
        <label>Building name <input name="name" placeholder="Main Building" required></label>
        <label>Short code <input name="code" placeholder="MAIN" required></label>
        <label>Description <textarea name="description" rows="2" placeholder="Central academic block"></textarea></label>
        ${this.stepActions(1, "Save building", "Add another building")}
      </form>
      ${this.createdList("Buildings added", rows)}`;
  },

  floorForm() {
    const buildings = this.state.data.buildings || [];
    const selected = this.state.lastBuildingId || (buildings[0] && buildings[0].id) || "";
    const nextNo = this.nextFloorNumber(selected);
    const options = buildings.map((b) =>
      `<option value="${b.id}" ${String(b.id) === String(selected) ? "selected" : ""}>${b.name}</option>`
    ).join("");
    const rows = (this.state.data.floors || []).map((f) =>
      `<li><b>${f.name}</b> · ${f.building_name}${f.description ? `<div class="sub">${f.description}</div>` : ""}</li>`
    ).join("");
    return `
      <p class="eyebrow">Step 2 of 4</p>
      <h2>Add floors</h2>
      <p class="muted">Save a floor, then use Add another floor for 2nd Floor, 3rd Floor, and so on.</p>
      <form id="setup-form" class="stack setup-form">
        <label>Building <select name="building_id" id="setup-building" required>${options}</select></label>
        <label>Floor number <input type="number" name="floor_number" id="setup-floor-no" value="${nextNo}" min="0" required></label>
        <label>Display name <input name="name" placeholder="1st Floor" required></label>
        <label>Description <textarea name="description" rows="2" placeholder="Lecture rooms and staff offices"></textarea></label>
        ${this.stepActions(2, "Save floor", "Add another floor")}
      </form>
      ${this.createdList("Floors added", rows)}`;
  },

  classroomForm() {
    const floors = this.state.data.floors || [];
    const selected = this.state.lastFloorId || (floors[0] && floors[0].id) || "";
    const options = floors.map((f) =>
      `<option value="${f.id}" ${String(f.id) === String(selected) ? "selected" : ""}>${f.building_name} · ${f.name}</option>`
    ).join("");
    const types = this.roomTypes.map((t) => `<option>${t}</option>`).join("");
    const rows = (this.state.data.classrooms || []).map((c) =>
      `<li><b>Room ${c.room_number}</b> · ${c.location} · ${c.capacity} seats${c.description ? `<div class="sub">${c.description}</div>` : ""}</li>`
    ).join("");
    return `
      <p class="eyebrow">Step 3 of 4</p>
      <h2>Add classrooms</h2>
      <p class="muted">Add every room on a floor. Use Add another room to keep going, then Continue.</p>
      <form id="setup-form" class="stack setup-form">
        <label>Floor <select name="floor_id" required>${options}</select></label>
        <label>Room number <input name="room_number" placeholder="204" required></label>
        <label>Student capacity <input type="number" name="capacity" min="1" value="60" required></label>
        <label>Type <select name="room_type">${types}</select></label>
        <label>Description <textarea name="description" rows="2" placeholder="Used for extra lectures and seminars"></textarea></label>
        <label>Facilities <input name="facilities" placeholder="Projector, AC"></label>
        ${this.stepActions(3, "Save classroom", "Add another room")}
      </form>
      ${this.createdList("Classrooms added", rows)}`;
  },

  slotForm() {
    const rows = (this.state.data.timeslots || []).map((s) =>
      `<li><b>${s.name}</b> · ${s.start_time} – ${s.end_time}${s.is_break ? " (break)" : ""}</li>`
    ).join("");
    return `
      <p class="eyebrow">Step 4 of 4</p>
      <h2>Add a time slot</h2>
      <p class="muted">Teaching periods such as 2:00 PM – 3:00 PM. You can add more than one period.</p>
      <form id="setup-form" class="stack setup-form">
        <label>Period name <input name="name" placeholder="Period 5" required></label>
        <label>Start <input type="time" name="start_time" value="14:00" required></label>
        <label>End <input type="time" name="end_time" value="15:00" required></label>
        <label>Sort order <input type="number" name="sort_order" value="${(this.state.data.timeslots || []).length + 1}"></label>
        <label class="check"><input type="checkbox" name="is_break"> This is a break</label>
        ${this.stepActions(4, "Save time slot", "Add another time slot")}
      </form>
      ${this.createdList("Time slots added", rows)}`;
  },

  bindForm() {
    const form = document.getElementById("setup-form");
    if (!form) return;
    const buildingSelect = form.querySelector("#setup-building");
    const floorNo = form.querySelector("#setup-floor-no");
    if (buildingSelect && floorNo) {
      buildingSelect.addEventListener("change", () => {
        floorNo.value = this.nextFloorNumber(buildingSelect.value);
      });
    }
    const back = form.querySelector("[data-back]");
    if (back) back.onclick = () => this.goTo(this.state.step - 1);
    const next = form.querySelector("[data-next]");
    if (next) next.onclick = () => this.goTo(this.state.step + 1);
    const addMore = form.querySelector("[data-add-more]");
    if (addMore) addMore.onclick = () => form.requestSubmit();
    const finish = form.querySelector("[data-finish]");
    if (finish) finish.onclick = () => this.closeAndReload();
    form.onsubmit = async (e) => {
      e.preventDefault();
      const payload = CIAS.formData(form);
      const urls = { 1: "/api/buildings", 2: "/api/floors", 3: "/api/classrooms", 4: "/api/timeslots" };
      const stay = this.state.step;
      if (this.state.step === 2) payload.floor_number = Number(payload.floor_number);
      if (this.state.step === 3) payload.capacity = Number(payload.capacity);
      if (this.state.step === 4) {
        payload.sort_order = Number(payload.sort_order || 0);
        payload.is_break = !!payload.is_break;
      }
      const res = await CIAS.api(urls[this.state.step], { method: "POST", body: payload });
      if (!res.ok) return CIAS.toast(res.error, "error");
      if (this.state.step === 1 && res.data) this.state.lastBuildingId = res.data.id;
      if (this.state.step === 2) {
        this.state.lastBuildingId = payload.building_id;
        if (res.data) this.state.lastFloorId = res.data.id;
      }
      if (this.state.step === 3) this.state.lastFloorId = payload.floor_id;
      CIAS.toast("Saved. You can add another, or Continue.", "success");
      const done = await this.refresh();
      if (done) return;
      this.goTo(stay);
    };
  },
};

document.addEventListener("DOMContentLoaded", () => CIASSetup.init());
