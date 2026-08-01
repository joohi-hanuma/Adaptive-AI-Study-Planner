# Adaptive-AI-Study-Planner
# 📚 Adaptive AI Study Planner using Agentic AI and LangGraph

An AI-powered study planning application that generates personalized study schedules using **Agentic AI**, **LangGraph**, and **Google Gemini API**. The system adapts study plans based on student progress, helping learners stay organized and achieve their academic goals efficiently.

---

## 📖 Introduction

The Adaptive AI Study Planner is an intelligent learning assistant that helps students create personalized study schedules, manage learning tasks, and monitor academic progress. Unlike traditional static timetables, this application dynamically updates study plans based on completed and pending tasks.

The project uses **Agentic AI** and **LangGraph** to coordinate multiple AI agents that collaborate to generate study plans, recommend learning resources, track progress, generate assessments, and automatically reschedule study sessions according to student performance.

---

## 🎯 Problem Statement

Students often struggle to manage multiple subjects, complete topics before deadlines, and maintain consistency in their studies. Traditional timetable applications generate fixed schedules that cannot adapt to changes in student progress.

This project addresses these challenges by providing an AI-powered adaptive study planner that continuously updates personalized study schedules according to user progress and learning requirements.

---

## ✨ Features

- 📅 Personalized AI Study Timetable
- 🤖 Multi-Agent Workflow using LangGraph
- 📚 AI-Based Resource Recommendations
- 📊 Progress Tracking Dashboard
- 🔄 Automatic Timetable Rescheduling
- 📝 AI Quiz & Assessment Generation
- ⏰ Deadline-Based Planning
- 🎨 Interactive Streamlit User Interface

---

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend Development |
| LangGraph | Multi-Agent Workflow |
| LangChain | LLM Integration |
| Google Gemini API | Large Language Model |
| Streamlit | User Interface |
| Pandas | Data Processing |
| NumPy | Numerical Computing |
| JSON | Local Data Storage |

---

## 🤖 AI Agents

### 1. Student Input Collector
Collects:
- Subjects
- Topics
- Deadlines
- Available Study Hours
- Preferred Session Duration
- Revision Preferences
- Assessment Frequency

### 2. Timetable Generator
Creates a personalized study timetable based on subject priority, deadlines, available study hours, and difficulty level.

### 3. Resource Recommendation Agent
Recommends study materials, tutorials, reference notes, and learning resources.

### 4. Progress Tracker
Tracks completed and pending tasks while monitoring overall study progress.

### 5. Adaptive Schedule Updater
Automatically updates future study schedules whenever tasks remain incomplete.

### 6. Assessment Generator
Generates quizzes, revision tests, and practice questions to evaluate learning progress.

---

## 🔄 Workflow

```text
Student Input
      │
      ▼
Student Input Collector
      │
      ▼
Timetable Generator
      │
      ▼
Resource Recommendation Agent
      │
      ▼
Assessment Generator
      │
      ▼
Progress Tracker
      │
      ▼
Adaptive Schedule Updater
      │
      ▼
Updated Personalized Study Plan
```

---

## 📝 Algorithm

### Inputs
- Subjects / Topics
- Study Deadlines
- Available Study Hours
- Preferred Session Duration
- Revision Preferences
- Assessment Frequency
- Task Completion Status

### Outputs
- Personalized Study Timetable
- AI-Recommended Learning Resources
- Periodic Assessments
- Adaptive Timetable Updates
- Progress Summary

### Steps

1. Start the application.
2. Collect student inputs.
3. Validate user information.
4. Send structured prompts to the Gemini LLM.
5. Analyze subject difficulty, deadlines, and available study hours.
6. Generate a personalized timetable.
7. Recommend learning resources.
8. Generate quizzes and revision schedules.
9. Display the study timetable.
10. Track completed and pending tasks.
11. Update future schedules if tasks remain incomplete.
12. Generate the final progress report.
13. End the application.

---

## 📂 Project Structure

```
Adaptive-AI-Study-Planner/
│── streamlit_app.py
│── study_planner.py
│── requirements.txt
│── README.md
│── .gitignore
│── assets/
│   ├── home.png
│   ├── timetable.png
│   ├── resources.png
│   ├── progress.png
│   └── assessment.png
```

---

## 🚀 Installation

```bash
git clone https://github.com/joohi-hanuma/Adaptive-AI-Study-Planner.git

cd Adaptive-AI-Study-Planner

pip install -r requirements.txt

streamlit run streamlit_app.py
```

---

## 📸 Screenshots

### 🏠 Home Page
(Add your application home page screenshot here.)

### 📅 Study Timetable
(Add timetable screenshot here.)

### 📚 Resource Recommendations
(Add resource recommendation screenshot here.)

### 📊 Progress Tracker
(Add progress dashboard screenshot here.)

### 📝 Assessment Generator
(Add assessment page screenshot here.)

---

## 🔮 Future Enhancements

- User Authentication
- SQLite/MySQL Database Integration
- Cloud Deployment
- Mobile Application
- Calendar Integration
- Email Notifications
- Voice-Based AI Assistant
- Learning Analytics Dashboard

---

## 👩‍💻 Author

**Joohi Hanuma**

B.Tech – Computer Science and Engineering

Internship Project – Adaptive AI Study Planner using Agentic AI and LangGraph

---

## 📄 License

This project is developed for educational and internship purposes.
