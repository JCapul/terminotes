const list = document.getElementById("notes-list");
const input = document.getElementById("search-input");
let notesCache = [];

function renderNotes(items) {
  if (!list) {
    return;
  }
  if (!items.length) {
    list.innerHTML = "<li>No notes found.</li>";
    return;
  }
  list.innerHTML = items
    .map(
      (note) => `
        <li>
          <a href="${note.url}">
            <h2>${note.title || "Untitled note"}</h2>
          </a>
          <p class="note-meta">Updated ${new Date(note.updated_at).toLocaleString()}</p>
          <p>${note.summary}</p>
          <p class="note-tags">Tags: ${note.tags.join(", ") || "–"}</p>
        </li>
      `
    )
    .join("\n");
}

async function loadNotes() {
  try {
    const response = await fetch("notes-data.json", { cache: "no-store" });
    notesCache = await response.json();
    renderNotes(notesCache);
  } catch (error) {
    console.error("Failed to load notes-data.json", error);
  }
}

if (input) {
  input.addEventListener("input", (event) => {
    const value = String(event.target.value || "").trim().toLowerCase();
    if (!value) {
      renderNotes(notesCache);
      return;
    }
    const filtered = notesCache.filter((note) => {
      return (
        note.title.toLowerCase().includes(value) ||
        note.description.toLowerCase().includes(value) ||
        note.body.toLowerCase().includes(value) ||
        note.tags.some((tag) => tag.toLowerCase().includes(value))
      );
    });
    renderNotes(filtered);
  });
}

loadNotes();
