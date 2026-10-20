# 🤝 Contributing to the `agent://` Protocol

Thanks for your interest in contributing to the `agent://` protocol! This repository hosts the development and discussion of the [Internet-Draft](https://datatracker.ietf.org/doc/draft-narvaneni-agent-uri/) proposing a URI-based framework for interoperable software agents.

We welcome feedback, discussion, and pull requests across all areas of the project — from the spec itself to reference implementations and ecosystem design.

---

## 📌 Ways You Can Contribute

### 💬 **Join the Discussion**
- Participate in [GitHub Discussions](https://github.com/agent-uri/agent-uri/discussions) to share questions, ideas, and feedback.
- Start or join a thread under categories like:
  - Draft Feedback
  - Implementations
  - Orchestration Patterns
  - Ecosystem / Integrations

### 📝 **Comment on the Draft**
- The current draft lives in [`/docs/rfc/`](https://github.com/agent-uri/agent-uri/tree/main/docs/rfc)
- You can:
  - Open an issue with suggested changes
  - Submit a pull request with improvements
  - Comment on specific text or patterns

### 🧪 **Build or Share Implementations**
- This repo hosts experiments and reference code.
- Add support for `agent://` to your own agent platform or framework.
- Share demos, use cases, or integrations!

### 📖 **Improve Documentation**
- Help clarify the spec or implementation notes.
- Add diagrams, examples, and tutorials.

---

## 🔧 How to Contribute

1. **Fork this repository**
2. **Create a new branch** for your contribution
3. **Make your changes** (draft edits, implementation code, docs, etc.)
4. **Submit a pull request** with a clear description of what you’re proposing

For changes to the Internet-Draft:
- Edits should be made to the latest revision in `docs/rfc/` (currently `draft-narvaneni-agent-uri-05.md`); earlier revisions are kept as published and should not be changed
- Run `scripts/build-draft.sh draft-narvaneni-agent-uri-NN` to regenerate the `.xml`, `.txt`, `.html` and `.pdf`. It needs [`kramdown-rfc`](https://github.com/cabo/kramdown-rfc) and [`xml2rfc`](https://ietf-tools.github.io/xml2rfc/), and produces the v3 XML that should be submitted to the datatracker
- Ensure that there are no warnings or errors from `kramdown-rfc` or `xml2rfc`
- We can help you with the tooling!

---

## 🔢 Version Management

### Single Source of Truth

The version is defined in **one place only**:

```python
# agent_uri/__init__.py
__version__ = "0.2.1"
```

### Version Update Process

When updating the version:

1. **Update `agent_uri/__init__.py`**:
   ```python
   __version__ = "x.y.z"
   ```

2. **Update `pyproject.toml`**:
   ```toml
   version = "x.y.z"  # Must match __init__.py
   ```

3. **That's it!** All other components will automatically use the correct version.

### How Components Get the Version

- **Submodules** (`common/`, `descriptor/`) import from main package
- **CLI** uses package metadata with fallback to imported version
- **Tests** should use flexible version checking, not hardcoded versions

### Testing Version Checks

```python
# ✅ Good - flexible version checking
assert "agent-uri" in result.stdout
assert any(char.isdigit() for char in result.stdout)

# ❌ Bad - hardcoded version
assert "agent-uri 0.2.1" in result.stdout
```

---

## 💬 Communication Channels

- 📄 [Internet-Draft on IETF Datatracker](https://datatracker.ietf.org/doc/draft-narvaneni-agent-uri/)
- 💬 [GitHub Discussions](https://github.com/agent-uri/agent-uri/discussions)
- ✉️ Email: (mailing list to be announced)

---

## 🧭 Project Goals

The `agent://` protocol is part of a broader vision to enable:
- Interoperable, URI-addressable agents
- A layered protocol model: addressing → discovery → orchestration
- Composable and collaborative multi-agent systems across ecosystems

Let’s shape the future of agent-native computing together!

— Yaswanth (@IvoryHeart)
