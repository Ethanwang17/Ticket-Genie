# Ticket Genie 🎟️

## Real-Time Show Alerts for Private Entertainment Platforms ⚡

Ticket Genie is a bot-powered solution for real-time discovery of newly released tickets on two private entertainment platforms: **FillASeat Las Vegas** and **House Seats Las Vegas**. By monitoring these sites 24/7 and delivering personalized show alerts directly via Discord, Ticket Genie eliminates the need for manual checking and transforms how users engage with time-sensitive membership benefits.

---

## Project Overview 📊

-   **95% uptime** maintained over 3+ months of continuous deployment
-   **1,000+ direct messages** sent to users with new show alerts
-   **60% of active users** customized their notifications using the in-app blacklist feature

Ticket Genie is a cloud-hosted, two-bot system that keeps a constant pulse on two invite-only ticket platforms and pushes personalized Discord alerts the moment new performances drop. Running 24/7 with a PostgreSQL backbone, it marries fast, headless scraping with per-user preferences so members never miss limited-availability shows again.

---

## The Challenge ⏳

Manually hunting for tickets on private entertainment sites is a race against the clock. Listings appear at unpredictable hours, disappear quickly, and live behind login walls that defeat ordinary RSS or push-notification tools.

**Key Challenges:**

-   Automating login, scraping, and parsing of websites with varying formats
-   Delivering notifications without overwhelming users
-   Providing per-user customization for alerts in a group communication environment

---

## Research & Discovery 🔍

The development process involved researching API-less scraping, handling authentication, managing rate limits, and balancing efficient data checks with timely user alerts. Focus was placed on Discord user experience, command interaction design, and database schema efficiency.

**Key Insights:**

-   Show alerts are time-sensitive and need <3 min alert delivery for high value
-   Blacklist/keyword filters to stop unwanted genres or venues from flooding DMs
-   Slash-command interface (e.g., `/blacklist add "Magic Show"`, `/alerts pause`) so non-technical users could self-service settings without bot restarts

---

## The Solution 🤖

A two-bot system (one for each platform) developed in Python, designed to run asynchronously, identify new shows, and notify users in near real-time with full database tracking and Discord interactivity.

-   **Automated Scrapers for FillASeat & House Seats:** Each bot handles login, parsing, and show extraction every 2–3 minutes.
-   **User-Specific Notification System:** Uses slash commands and user-specific blacklists to send DM alerts only for unfiltered shows.
-   **Cloud-Based Architecture:** Containerized deployment with persistent PostgreSQL integration and environment-based secrets for security.

---

## Results & Impact 🚀

Ticket Genie has been running continuously, serving real-time alerts to a private Discord server. User testing confirmed increased satisfaction and decreased time spent browsing ticket websites.

> "I used to cycle through both sites all day to see sold-out notices. Now Ticket Genie pings me and tickets are secured with no stress."
> — Avid Ticket Genie user

---

## Technologies Used 🛠️

-   Python
-   Discord API
-   PostgreSQL
-   Selenium
-   Docker

---
