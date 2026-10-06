const booksBody = document.querySelector('#booksBody');
const emptyState = document.querySelector('#emptyState');
const searchInput = document.querySelector('#searchInput');
const bookDialog = document.querySelector('#bookDialog');
const issueDialog = document.querySelector('#issueDialog');
const bookForm = document.querySelector('#bookForm');
const issueForm = document.querySelector('#issueForm');
const toast = document.querySelector('#toast');
let currentStatus = 'All';
let issueBookId = null;
let searchTimer;

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#039;', '"':'&quot;' }[char]));
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.error || 'Something went wrong.');
  return data;
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle('error', isError);
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 3000);
}

function borrower(book) {
  if (!book.member_name) return '<span>—</span>';
  return `<div class="borrower"><b>${escapeHtml(book.member_name)}</b><br><span>Issued ${escapeHtml(book.issued_on)}</span></div>`;
}

function renderBooks(books) {
  emptyState.hidden = books.length !== 0;
  booksBody.innerHTML = books.map(book => `
    <tr>
      <td><div class="book-title">${escapeHtml(book.title)}</div><div class="book-author">${escapeHtml(book.author)}</div></td>
      <td><span class="category">${escapeHtml(book.category)}</span></td>
      <td>${escapeHtml(book.isbn)}</td>
      <td><span class="status ${book.availability_status === 'Available' ? 'available' : 'issued'}">${escapeHtml(book.availability_status)}</span></td>
      <td>${borrower(book)}</td>
      <td><div class="action-row">
        ${book.availability_status === 'Available' ? `<button class="text-action" data-issue="${book.id}" data-title="${escapeHtml(book.title)}">Issue</button>` : `<button class="text-action" data-return="${book.id}">Return</button>`}
        <button class="text-action delete" data-delete="${book.id}" data-title="${escapeHtml(book.title)}">Delete</button>
      </div></td>
    </tr>`).join('');
}

async function loadBooks() {
  const params = new URLSearchParams({ q: searchInput.value.trim(), status: currentStatus });
  try { renderBooks(await request(`/api/books?${params}`)); }
  catch (error) { showToast(error.message, true); }
}

async function loadStats() {
  try {
    const data = await request('/api/stats');
    document.querySelector('#totalStat').textContent = data.total;
    document.querySelector('#availableStat').textContent = data.available;
    document.querySelector('#issuedStat').textContent = data.issued;
    document.querySelector('#memberStat').textContent = data.members;
  } catch (error) { showToast(error.message, true); }
}

async function refresh() { await Promise.all([loadBooks(), loadStats()]); }

document.querySelector('#openAdd').addEventListener('click', () => bookDialog.showModal());
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => document.querySelector(`#${button.dataset.close}`).close()));
document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
  currentStatus = button.dataset.status;
  document.querySelectorAll('.filter').forEach(item => item.classList.toggle('active', item === button));
  loadBooks();
}));
searchInput.addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadBooks, 220); });

bookForm.addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(bookForm));
  try {
    await request('/api/books', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
    bookForm.reset(); bookDialog.close(); showToast('Book added to the collection.'); refresh();
  } catch (error) { showToast(error.message, true); }
});

issueForm.addEventListener('submit', async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(issueForm));
  try {
    await request(`/api/books/${issueBookId}/issue`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
    issueForm.reset(); issueDialog.close(); showToast('Book issued successfully.'); refresh();
  } catch (error) { showToast(error.message, true); }
});

booksBody.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button) return;
  if (button.dataset.issue) {
    issueBookId = button.dataset.issue;
    document.querySelector('#issueTitle').textContent = `Issue “${button.dataset.title}”`;
    issueDialog.showModal();
  }
  if (button.dataset.return) {
    try { await request(`/api/books/${button.dataset.return}/return`, { method:'POST' }); showToast('Book returned to the library.'); refresh(); }
    catch (error) { showToast(error.message, true); }
  }
  if (button.dataset.delete) {
    if (!confirm(`Delete “${button.dataset.title}” from the library?`)) return;
    try { await request(`/api/books/${button.dataset.delete}`, { method:'DELETE' }); showToast('Book deleted.'); refresh(); }
    catch (error) { showToast(error.message, true); }
  }
});

refresh();
