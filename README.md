# 🏦 Agentic Financial Intelligence Platform

> Enterprise-grade multi-agent AI system that automates financial research using LangGraph, LlamaIndex, SEC EDGAR, and OpenAI — reducing research time from hours to minutes.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4.8-green)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.45-red)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 What It Does

Given a stock ticker (e.g. `AAPL`, `MSFT`, `TSLA`), this platform automatically:

1. **Retrieves** real 10-K, 10-Q filings from SEC EDGAR
2. **Extracts** financial metrics (revenue, EPS, margins, ratios) via XBRL
3. **Values** the company using DCF model + comparable analysis
4. **Analyzes** news sentiment from multiple sources
5. **Answers** questions from actual filing documents using RAG
6. **Generates** a professional investment memo using GPT-4o-mini
7. **Creates** a downloadable DOCX investment report
8. **Validates** all outputs with a 14-point QA check

**Result:** A complete investment research package in under 3 minutes.

---

## 🏗️ Architecture