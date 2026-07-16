# Campus Facility Helpdesk System

## 📖 Overview
The Campus Facility Helpdesk is a web application designed to make reporting and fixing issues on a college campus easy and efficient. Think of it as a digital ticketing system. When a faculty member finds an issue (like a broken projector or a leaking AC), they can scan a QR code in the room and quickly submit a "ticket" (a request for help). The maintenance staff (attenders) receive these tickets in real-time and can accept and resolve them. Finally, an admin oversees the entire process through a dashboard that tracks how quickly issues are fixed and monitors user satisfaction.

## 🛠 Technologies Used
Here is a breakdown of the technologies used, explained simply:

### 1. Python & Django (The Backend Engine)
*   **Python:** The main programming language used to write the logic of the application. It's known for being readable and straightforward.
*   **Django:** A powerful web framework built on top of Python. Imagine Django as a pre-built foundation for a house. Instead of building the plumbing and electrical wiring from scratch (like security, database connection, user logins), Django provides these out of the box so you can focus on building the specific features of your app.

### 2. SQLite (The Database)
*   **SQLite:** This is the default database used in Django. It stores all the information for our application (users, tickets, rooms, etc.) in a single file (`db.sqlite3`). It is lightweight and perfect for development and small-scale projects without needing a complex database server setup.

### 3. Django Channels & WebSockets (Real-Time Magic)
*   **WebSockets:** Traditional websites work on a "request-response" model (you click a link, the server sends a new page). WebSockets keep a continuous connection open between the browser and the server.
*   **Django Channels:** An extension for Django that allows it to handle WebSockets. This is what powers the **real-time notifications** in the app. When a faculty member creates a ticket, the attender gets notified instantly without having to refresh the page!

### 4. HTML, CSS & JavaScript (The Frontend / User Interface)
*   **HTML:** The structure of the web pages (buttons, text, forms).
*   **CSS / Bootstrap 5:** Bootstrap is a CSS framework that makes styling easy. It helps make the website look modern, responsive (works well on phones and laptops), and clean without writing thousands of lines of custom CSS.
*   **JavaScript & Chart.js:** JavaScript adds interactivity to the website. The admin dashboard uses a library called **Chart.js** to draw beautiful graphs (like pie charts and line charts) showing ticket statistics.

### 5. QR Code Generation (The Smart Scanning)
*   **qrcode library:** A Python tool used to automatically generate a unique QR Code image for every room created in the system. When scanned with a phone, it redirects the user straight to the ticket-raising page for that specific room.

## 🚀 How the Flow Works
1.  **Admin** creates Departments, Rooms, and User Accounts.
2.  The system automatically generates a **QR Code** for each room.
3.  **Faculty** scans the QR code, logs in, and reports an issue (e.g., "Projector not working").
4.  **Attenders** (maintenance staff) assigned to that department get a real-time notification.
5.  An Attender accepts the ticket, goes to the room, fixes the issue, and marks it as "Completed".
6.  The **Faculty** can then rate the service out of 5 stars.
7.  The **Admin** views the analytics (average fixing time, number of complaints, etc.) on their dashboard.
