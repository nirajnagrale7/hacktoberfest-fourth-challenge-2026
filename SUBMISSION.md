---
title: "SlothSort: A Local AI Assistant for the Downloads Folder"
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3:
Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built

SlothSort helps tidy a folder without the tedious drag-and-drop routine. It
looks at filenames, asks a local AI model to suggest categories and clearer
names, and presents the proposed moves for review. Files are only moved after
the user confirms the plan.

## Demo

The project currently runs locally. Install the dependencies and follow the
Ollama setup in the [README](./README.md). There is no public demo yet.

## Code

[View the source code on GitHub](https://github.com/nirajnagrale7/hacktoberfest-first-challenge-2026/tree/main/Challenge%204).

## How I Built It

The interface uses Streamlit, and the app asks a local Ollama server to run the
open-weight `qwen2.5:3b` model. The model sees filenames only and returns a
category plus a suggested name. The Python app validates that response,
sanitizes names, checks for conflicts, and requires explicit approval before
moving anything.

## Why Does Open Innovation Matter?

Filenames can contain personal or work-related details. Local inference keeps
them on the user's machine rather than sending them to a cloud API. After the
one-time model download, there is no per-file inference fee. The prompt,
category list, and model choice are all open to inspection and change.

## My Agent Session

I do not have a shareable DevRelay session link for this project.

## The Lazy Payoff

SlothSort turns a pile of filenames into a proposed folder structure in one
step, while keeping the final decision with the user. Add a real time-saved
estimate here after trying it on a folder and timing the manual alternative.

## Prize Categories

Hacktoberfest Open-Source AI Challenge: Slow and Steady.
