# Leafline Library Management System

Leafline is a full-stack Library Management System that helps a librarian maintain a book collection and track who has borrowed each book. It provides a simple responsive dashboard for adding, searching, issuing, returning, and deleting books.

## Features

- Add books with title, author, ISBN, and category
- View the complete collection with live availability statistics
- Search by title, author, ISBN, or category
- Filter available and issued books
- Issue a book to a member using their name and email address
- Return a book to the library
- Delete book records
- Prevent duplicate ISBN entries and double issuing
- Store book and member data persistently in SQLite

## Technologies and Tools Used

- **Frontend:** HTML5, CSS3, JavaScript, Fetch API
- **Backend:** Python, Flask
- **Database:** SQLite
- **Tooling:** Node.js/npm scripts, Git, GitHub

## How to Run the Project

### Requirements

- Python 3.10 or later
- pip

### Steps

1. Clone or download this repository.
2. Open a terminal in the project folder.
3. Install the required package:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   python app.py
   ```

   If Node.js is installed, you may instead use:

   ```bash
   npm start
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

The SQLite database is created automatically the first time the application runs, with a small sample book collection.

## Project Structure

```
app.py              Flask application and REST API
templates/          HTML page
static/             CSS and JavaScript files
requirements.txt    Python dependencies
package.json        Node.js tooling scripts
```

## Testing

The following behaviours were tested:

- Adding a book
- Searching books
- Preventing duplicate ISBN values
- Issuing a book
- Preventing a book from being issued twice
- Returning a book
- Preventing return of an unissued book
- Deleting a book and handling missing records
