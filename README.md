# AI-requests-board

## Overview
This project provides a lightweight exchange system for AI assistance.  Users
spend **tokens** to post requests and can reward helpful replies with tokens in
return.  A small Python server manages tasks, replies and token balances using
SQLite and simple HTTP endpoints.  Configuration is read from a `.env` file (see
`.env.example`).

Participants first obtain a temporary **User ID** (`POST /register`) which
expires after 24 hours. One token can be earned for free by reading the article
at [authenticodev.com/better-choices](https://authenticodev.com/better-choices)
and submitting its proof via `POST /earn`.

### Core Idea

Create a two-column bulletin board where people post AI-powered requests and volunteers pick them up to deliver outputs. Each completed task nets the volunteer a “Help Stub” they can redeem later for someone else’s help or AI output.
What You Need

    A whiteboard/corkboard or even a blank wall

    Two stacks of index cards (or Post-its) and pens

    A simple “Help Stub” template (a blank card you tear in half)

How It Works

    Columns Setup

        Left Side – “Request”: People write on a card

            “Generate a haiku about summer storms”

            “Outline a 200-word blog intro on remote work”

        Right Side – “Volunteer”: Folks pick a Request card and move it here when they start it.

    Delivery & Reward

        When done, volunteer sticks the completed output (printed or photographed) under the Request.

        They tear off a “Help Stub” (half the card) from a stub-stack and keep it.

    Stubs as Currency

        Anytime they want an AI favor—any request from the board—they hand in a Help Stub to the original poster (or to you as organizer).

        You tear off another stub for them to spend next time: peer-to-peer exchange.

Why It Fits Your Goals

    Zero tech overhead: uses paper and wall space you already have.

    Built-in exchange: stubs are both currency and proof of contribution.

    Demand-channeling: you capture ongoing requests and funnel them to active volunteers.

    Prompt-tuning on the fly: as organizer, you can toss out “pro tips” on how to sharpen prompts, guiding everyone.

Next Steps (5 min)

    Label your board “AI Task Board” with two columns.

    Prep a stack of Request cards and matching stub-cards.

    Announce: “Any AI task you need, post it—anyone can pick it up, earn a stub, spend it later!”

Within ten minutes you have a self-sustaining, exchange-based AI creation hub, seeding both creative outputs and a little “buying-power” in the form of Help Stubs.


Here’s how you can run the “AI Task Board Exchange” entirely online, with digital requests, submissions, and stub-tokens:

---

## 1. Choose Your Virtual Space

Pick a lightweight collaboration tool you already use—e.g.:

* **Discord** (free, bots available)
* **Slack** (if you already have a workspace)
* **Trello** or **Notion** board

---

## 2. Set Up Your “Board”

Create three columns (or channels):

1. **📝 Requests**
2. **🚧 In Progress**
3. **✅ Completed**

---

## 3. Handling Requests & Volunteers

1. **Post a Request**

   * Any participant adds a card/post in **📝 Requests**, e.g.:

     ```
     Title: Haiku about summer storms  
     Details: “3 lines, vivid imagery, <#channel> tag when done.”  
     Reward: 1 Help-Stub  
     ```

2. **Claim a Task**

   * A volunteer drags that card to **🚧 In Progress** (or adds a reaction like 🎯).

---

## 4. Returning the AI-Generated Response

1. Volunteer runs the request through the AI (ChatGPT, Midjourney, etc.).

2. They **reply** to the original card/post with:

   * **Attachment** (text snippet, image file, link)
   * A short “Done!” message tagging the requester (e.g. `@alice here’s your haiku!`)

3. They then move the card to **✅ Completed**.

---

## 5. Issuing & Tracking Help-Stubs

1. **Automated Bot** (if you have one)

   * A simple Discord/Slack bot can watch for the “Done!” message in **✅ Completed** and auto-DM the volunteer a stub-credit.

2. **Manual Ledger** (if you want zero-tech)

   * Maintain a shared spreadsheet (Google Sheets) with two columns: **User** and **Stubs Earned**.
   * When a card hits **✅ Completed**, the organizer or the requester increments that volunteer’s row by +1.

Participants can check their stub-balance anytime via the sheet link or a bot command (`!stubs @bob`).

---

## 6. Redeeming Stubs

* To spend a stub, a user simply adds a new Request card and writes “Paid with 1 stub” in the Reward field.
* The organizer (or bot) verifies their stub-balance ≥ 1, then decrements it by 1 when someone claims and completes it.

---

## 7. Optional Enhancements

* **Leaderboard** channel or widget showing top helpers.
* **Stub Gifts**: let people transfer stubs by “/give 1 stub @user.”
* **Themes & Badges**: special badges for 5-stub contributors, or theme-weeks (poetry, memes, logos).

---

### Why This Works Virtually

* **Instant feedback loop**: requests → AI output → stub reward → next request.
* **Minimal friction**: uses platforms people already know.
* **Clear currency**: digital “Help-Stubs” tracked in one place, no printing or physical tokens.
* **Scalable**: you can spin it up in 10 minutes and grow it organically.

With this flow, every AI response is returned right in your virtual board, and once it lands in “Completed,” the stub-token is issued immediately—either automatically via a bot or manually via your ledger. Enjoy your fully virtual AI exchange hub!

---
## Running the Python server

This repository now includes a minimal HTTP server written with the Python standard library. It exposes a small API for posting tasks, claiming them, completing them and tracking "Help Stub" balances.

### Local development

First copy `.env.example` to `.env` and adjust settings if needed.

```bash
cp .env.example .env
python server/main.py
```

The service listens on the port specified in `.env` (`8080` by default) and stores
data in the configured SQLite database file.

### API Overview

Tokens act as currency. Creating a task costs 1 token from the requester.
Accepting or rewarding a reply also costs the requester 1 token and rewards the volunteer.

Every action uses a temporary **User ID** generated with `POST /register`. IDs expire after 24 hours.

* `POST /register` – generate a new temporary user ID
* `POST /earn` `{ "user": "ID", "code": "CODE" }` – redeem the article proof for 1 token
* `POST /tokens` `{ "user": "ID", "amount": 5 }` – add tokens to a user
* `GET /tokens` – list token balances
* `POST /tasks` `{ "title": "T", "details": "D", "requester": "ID" }` – create task (spends 1 token)
* `GET /tasks` – list tasks
* `POST /tasks/<id>/replies` `{ "user": "ID", "content": "answer" }` – add a reply
* `GET /tasks/<id>/replies` – list replies for a task
* `POST /replies/<id>/accept` – requester accepts a reply (transfers 1 token)
* `POST /replies/<id>/valuable` – mark a reply as valuable (also transfers 1 token)

### Token system module

Token management has been extracted to `tokens.py`. Any Python service can import
`TokenSystem` to use the same SQLite database for users and token balances:

```python
from tokens import TokenSystem
ts = TokenSystem('board.db')
```

The HTTP server in `server/main.py` uses this module but other programs can
integrate with it as well.

### Docker

A `Dockerfile` is provided to run the server in a container. Build and run it like so:

```bash
docker build -t ai-board .
docker run -d --name ai-board --network my-network \
  -p 8080:8080 --env-file .env ai-board
```
Replace `my-network` with the docker network connected to your Caddy proxy. The `.env` file controls the port and database path used inside the container.

