# Master Sprint Management - User Guide

Welcome to the **Master Sprint Management** addon for Odoo 15. This module is designed to bring a high-performance, Jira-like agile experience to your Odoo projects.

---

## 🚀 1. Getting Started

### Enable Sprint Management
To use these features on a project:
1. Go to **Project Settings**.
2. Tick the **Use Sprint Management** checkbox.
3. This will activate the "Backlog", "Create Sprint", and "Epics" buttons on the project dashboard.

---

## 📋 2. Planning (The Backlog)

The **Planning** view is your central hub for project organization.
- **Backlog Pool**: All tasks not yet assigned to a sprint.
- **Planned Sprints**: Sprints in the "Waiting" state.
- **Drag & Drop**: Easily move tasks between the backlog and various planned sprints to organize your roadmap.

---

## 🆕 3. Creating a Sprint

Instead of just adding a record, use the **Create Sprint** button:
1. **Details**: Set the Sprint name (auto-suggested as Month Year), Duration, and Start Date.
2. **Backlog Selection**: Use the **"Select Backlog Tasks"** field to pull in existing work into your new sprint immediately.
3. **Sprint Goal**: Define why this sprint exists.

---

## ▶️ 4. Starting a Sprint

Once your plan is ready:
1. Open the planned sprint and click **Start Sprint**.
2. A wizard will appear showing you a **Summary** of the tasks included.
3. Choose a **Duration Preset** (1, 2, or 4 weeks) to automatically calculate the finish date.
4. Once started, the sprint becomes **Active**, and the **Sprint Board** is updated.

---

## 📊 5. The Sprint Board

Use the **Sprint Board** to track daily progress:
- **Banner**: Displays the Sprint Name, Dates, and **Sprint Goal** at the top.
- **Quick Navigation**: Use the **"Planning"** button to jump back to the backlog or **"Complete Sprint"** when done.
- **Visuals**: Kanban cards show Epic and Sprint badges for clear identification.

---

## 🚩 6. Epic Management

Group related work under **Epics**:
- Check the **Epic Progress** on the Project form.
- View completion percentages to see how close you are to finishing major milestones.
- Filter and Group tasks by Epic in all views.

---

## ✅ 7. Closing a Sprint

When the time is up, click **Complete Sprint**:
1. **Summary**: See exactly how many tasks were finished vs. remain open.
2. **Handle Incomplete Work**:
   - **New Sprint**: System automatically creates next month's sprint and moves tasks there.
   - **Existing Sprint**: Pick another planned sprint from the list.
   - **Backlog**: Move tasks back to the general pool.
3. **Sprint Report**: Access the **Sprint Report** tab on closed sprints to see historical snapshot data (what was finished at the moment of closing).

---

## 🛠️ Tips for Success
- **Automatic Naming**: Sprints are named like "Ocak 26" based on their start date.
- **Datetime Precision**: All dates use precise time tracking for accurate sprint boundaries.
- **Seamless Flow**: Use the "Planning" button on the board to quickly adjust your backlog without leaving your workflow.
