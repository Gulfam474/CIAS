const CIASTour = {
  index: 0,
  steps: [],

  catalog: [
    {
      id: "dashboard",
      title: "Dashboard",
      text: "Your home screen. See campus totals, who the admins are, and current occupancy at a glance.",
    },
    {
      id: "search",
      title: "Find Classroom",
      text: "The main job of CIAS. Choose day, time, building and student count to list rooms that are free and large enough.",
    },
    {
      id: "occupancy",
      title: "Occupancy",
      text: "See every classroom for a period — available or already in use — without guessing from the paper timetable.",
    },
    {
      id: "bookings",
      title: "Bookings",
      text: "Reserve a free room for an extra class, replacement lecture or meeting. Occupied rooms cannot be booked.",
    },
    {
      id: "buildings",
      title: "Buildings & floors",
      text: "Keep the campus map here: add buildings, then as many floors as you need, each with a description.",
    },
    {
      id: "classrooms",
      title: "Classrooms",
      text: "Store room number, student capacity, type and description. Search uses this capacity to pick a suitable room.",
    },
    {
      id: "timeslots",
      title: "Time slots",
      text: "College periods such as 2:00 PM – 3:00 PM. Breaks are marked so they cannot be booked.",
    },
    {
      id: "timetable",
      title: "Timetable",
      text: "Regular class allocations. A room with a timetable entry is treated as occupied for that day and period.",
    },
    {
      id: "reports",
      title: "Reports",
      text: "Weekly utilization and seat capacity by building, useful for the administrator’s review.",
    },
    {
      id: "users",
      title: "Users & roles",
      text: "Super Admins assign access here: Super Admin, Admin or Staff. This is how you identify who is an admin.",
    },
    {
      id: "account",
      title: "Your account",
      text: "Your name and role stay visible here. Open Profile to update details, or Sign out when you are done.",
    },
  ],

  init() {
    document.querySelectorAll("[data-start-tour]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        this.start();
      });
    });
  },

  collectSteps() {
    return this.catalog.filter((step) => document.querySelector(`[data-tour="${step.id}"]`));
  },

  start() {
    this.steps = this.collectSteps();
    if (!this.steps.length) return;
    this.index = 0;
    this.ensureDom();
    this.root.hidden = false;
    document.body.classList.add("tour-open");
    this.render();
  },

  ensureDom() {
    if (this.root) return;
    this.root = document.createElement("div");
    this.root.className = "tour-overlay";
    this.root.id = "product-tour";
    this.root.innerHTML = `
      <div class="tour-spot" id="tour-spot"></div>
      <aside class="tour-card" id="tour-card">
        <button type="button" class="toast-x" data-tour-close aria-label="Close">×</button>
        <p class="eyebrow" id="tour-progress"></p>
        <h3 id="tour-title"></h3>
        <p id="tour-text"></p>
        <div class="tour-dots" id="tour-dots"></div>
        <div class="tour-actions">
          <button type="button" class="btn" data-tour-skip>Skip</button>
          <button type="button" class="btn" data-tour-prev>Back</button>
          <button type="button" class="btn primary" data-tour-next>Next</button>
        </div>
      </aside>`;
    document.body.appendChild(this.root);
    this.root.querySelector("[data-tour-skip]").onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.finish();
    };
    this.root.querySelector("[data-tour-close]").onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.finish();
    };
    this.root.querySelector("[data-tour-prev]").onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.go(-1);
    };
    this.root.querySelector("[data-tour-next]").onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.go(1);
    };
    this.root.addEventListener("click", (e) => e.stopPropagation());
    document.addEventListener("click", this.guardNav, true);
    window.addEventListener("resize", () => {
      if (!this.root || this.root.hidden) return;
      this.place();
    });
  },

  guardNav(e) {
    if (!document.body.classList.contains("tour-open")) return;
    const link = e.target.closest("a");
    if (link && link.closest(".sidebar")) {
      e.preventDefault();
      e.stopPropagation();
    }
  },

  go(delta) {
    const next = this.index + delta;
    if (next < 0) return;
    if (next >= this.steps.length) {
      this.finish();
      return;
    }
    this.index = next;
    this.render();
  },

  render() {
    const step = this.steps[this.index];
    const last = this.index === this.steps.length - 1;
    document.getElementById("tour-progress").textContent =
      `Product tour · ${this.index + 1} of ${this.steps.length}`;
    document.getElementById("tour-title").textContent = step.title;
    document.getElementById("tour-text").textContent = step.text;
    this.root.querySelector("[data-tour-prev]").disabled = this.index === 0;
    this.root.querySelector("[data-tour-next]").textContent = last ? "Finish" : "Next";
    document.getElementById("tour-dots").innerHTML = this.steps
      .map((_, i) => `<i class="${i === this.index ? "is-on" : ""}"></i>`)
      .join("");
    this.place();
  },

  place() {
    const step = this.steps[this.index];
    const target = document.querySelector(`[data-tour="${step.id}"]`);
    const spot = document.getElementById("tour-spot");
    const card = document.getElementById("tour-card");
    document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target"));
    if (!target) {
      spot.style.display = "none";
      return;
    }
    spot.style.display = "block";
    target.classList.add("tour-target");
    const nav = document.querySelector(".sidebar nav");
    if (nav && nav.contains(target)) {
      target.scrollIntoView({ block: "center", inline: "nearest" });
    }
    const box = target.getBoundingClientRect();
    const pad = 6;
    spot.style.top = `${Math.max(8, box.top - pad)}px`;
    spot.style.left = `${Math.max(8, box.left - pad)}px`;
    spot.style.width = `${box.width + pad * 2}px`;
    spot.style.height = `${box.height + pad * 2}px`;
    card.style.top = "50%";
    card.style.right = "28px";
    card.style.left = "auto";
    card.style.transform = "translateY(-50%)";
  },

  finish() {
    document.querySelectorAll(".tour-target").forEach((el) => el.classList.remove("tour-target"));
    document.body.classList.remove("tour-open");
    if (this.root) this.root.hidden = true;
  },
};

document.addEventListener("DOMContentLoaded", () => CIASTour.init());
window.CIASTour = CIASTour;
