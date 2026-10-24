const taskList = document.querySelector("#task-list");
const taskTemplate = document.querySelector("#task-template");
const taskForm = document.querySelector("#task-form");
const taskTitle = document.querySelector("#task-title");
const taskDescription = document.querySelector("#task-description");
const formMessage = document.querySelector("#form-message");
const apiStatus = document.querySelector("#api-status");
const apiStatusLabel = document.querySelector("#api-status-label");
const filterButtons = [...document.querySelectorAll(".filter-tab")];

let tasks = [];
let activeFilter = "all";

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new Error("Could not reach the API. Check that the app is running.");
  }

  if (!response.ok) {
    if (response.status === 503) {
      throw new Error("The database is unavailable. Start the database and try again.");
    }
    if (response.status === 422) {
      throw new Error("Please check the task details and try again.");
    }
    throw new Error(`The request could not be completed (${response.status}).`);
  }

  if (response.status === 204) return null;
  return response.json();
}

function setApiStatus(online) {
  apiStatus.classList.toggle("is-online", online);
  apiStatus.classList.toggle("is-offline", !online);
  apiStatusLabel.textContent = online ? "API connected" : "API unavailable";
}

function setFormMessage(message, success = false) {
  formMessage.textContent = message;
  formMessage.classList.toggle("is-success", success);
}

function updateOverview() {
  const complete = tasks.filter((task) => task.completed).length;
  const remaining = tasks.length - complete;
  const progress = tasks.length ? Math.round((complete / tasks.length) * 100) : 0;

  document.querySelector("#remaining-count").textContent = remaining;
  document.querySelector("#remaining-label").textContent = remaining === 1 ? "thing to do" : "things to do";
  document.querySelector("#completed-count").textContent = complete;
  document.querySelector("#task-total").textContent = tasks.length;
  document.querySelector("#progress-label").textContent = `${progress}%`;
  document.querySelector("#progress-fill").style.width = `${progress}%`;
  document.querySelector("#progress-track").setAttribute("aria-valuenow", progress);
}

function showEmptyState() {
  const messages = {
    all: ["A clear page is a lovely start.", "Add a task when something comes to mind."],
    active: ["Nothing waiting on you.", "You have no open tasks right now."],
    completed: ["Your wins will show up here.", "Complete a task and it will land in this list."],
  };
  const [title, description] = messages[activeFilter];
  const empty = document.createElement("div");
  empty.className = "empty-state";
  const icon = document.createElement("span");
  icon.className = "empty-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "✳";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.textContent = description;
  empty.append(icon, heading, copy);
  taskList.replaceChildren(empty);
}

function taskDate(value) {
  if (!value) return "Added just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Added recently";
  return `Added ${new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date)}`;
}

function renderTasks() {
  updateOverview();

  const visible = [...tasks]
    .sort((a, b) => b.id - a.id)
    .filter((task) => {
      if (activeFilter === "active") return !task.completed;
      if (activeFilter === "completed") return task.completed;
      return true;
    });

  if (!visible.length) {
    showEmptyState();
    return;
  }

  const cards = visible.map((task) => {
    const fragment = taskTemplate.content.cloneNode(true);
    const item = fragment.querySelector(".task-item");
    const toggle = fragment.querySelector(".task-toggle");
    const title = fragment.querySelector(".task-name");
    const description = fragment.querySelector(".task-description");
    const state = fragment.querySelector(".task-state");
    const date = fragment.querySelector(".task-date");
    const remove = fragment.querySelector(".delete-task");

    item.classList.toggle("is-completed", task.completed);
    title.textContent = task.title;
    description.textContent = task.description || "";
    description.hidden = !task.description;
    state.textContent = task.completed ? "Completed" : "In progress";
    date.textContent = taskDate(task.created_at);
    date.dateTime = task.created_at || "";
    toggle.setAttribute("aria-label", task.completed ? "Mark task in progress" : "Mark task complete");

    toggle.addEventListener("click", async () => {
      toggle.disabled = true;
      try {
        const updated = await apiRequest(`/tasks/${task.id}`, {
          method: "PUT",
          body: JSON.stringify({
            title: task.title,
            description: task.description,
            completed: !task.completed,
          }),
        });
        tasks = tasks.map((entry) => entry.id === updated.id ? updated : entry);
        renderTasks();
      } catch (error) {
        toggle.disabled = false;
        setFormMessage(error.message);
      }
    });

    remove.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        await apiRequest(`/tasks/${task.id}`, { method: "DELETE" });
        tasks = tasks.filter((entry) => entry.id !== task.id);
        renderTasks();
      } catch (error) {
        remove.disabled = false;
        setFormMessage(error.message);
      }
    });

    return fragment;
  });

  taskList.replaceChildren(...cards);
}

async function loadTasks() {
  taskList.setAttribute("aria-busy", "true");
  try {
    const [items] = await Promise.all([
      apiRequest("/tasks"),
      apiRequest("/ready"),
    ]);
    tasks = items;
    setApiStatus(true);
    document.querySelector("#list-footer-label").textContent = "Your list is up to date";
    renderTasks();
  } catch (error) {
    setApiStatus(false);
    const panel = document.createElement("div");
    panel.className = "error-state";
    const heading = document.createElement("h3");
    heading.textContent = "We couldn't load your tasks.";
    const copy = document.createElement("p");
    copy.textContent = error.message;
    panel.append(heading, copy);
    taskList.replaceChildren(panel);
    document.querySelector("#list-footer-label").textContent = "Waiting for the API";
  } finally {
    taskList.setAttribute("aria-busy", "false");
  }
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = taskTitle.value.trim();
  if (!title) {
    taskTitle.focus();
    return;
  }

  const button = taskForm.querySelector("button[type='submit']");
  button.disabled = true;
  button.querySelector("span:nth-child(2)").textContent = "Adding…";
  setFormMessage("");

  try {
    const created = await apiRequest("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title,
        description: taskDescription.value.trim() || null,
        completed: false,
      }),
    });
    tasks.push(created);
    activeFilter = "all";
    filterButtons.forEach((filterButton) => {
      const selected = filterButton.dataset.filter === activeFilter;
      filterButton.classList.toggle("is-active", selected);
      filterButton.setAttribute("aria-selected", String(selected));
    });
    taskForm.reset();
    setFormMessage("Added to your list. One step at a time.", true);
    renderTasks();
    taskTitle.focus();
  } catch (error) {
    setFormMessage(error.message);
  } finally {
    button.disabled = false;
    button.querySelector("span:nth-child(2)").textContent = "Add to my list";
  }
});

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    filterButtons.forEach((filterButton) => {
      const selected = filterButton === button;
      filterButton.classList.toggle("is-active", selected);
      filterButton.setAttribute("aria-selected", String(selected));
    });
    renderTasks();
  });
});

document.querySelector("#refresh-button").addEventListener("click", loadTasks);

loadTasks();
