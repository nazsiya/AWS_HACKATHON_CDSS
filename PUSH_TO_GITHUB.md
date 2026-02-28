# Push to GitHub & Give Team Access

## Step 1: Create the repository on GitHub

**Option A — Using the GitHub website**

1. Go to [github.com](https://github.com) and sign in.
2. Click **+** (top right) → **New repository**.
3. Set:
   - **Repository name:** `CDSS` (or e.g. `cdss-hospital`)
   - **Description:** `Clinical Decision Support System - Multi-agent AI platform for Indian hospitals`
   - **Visibility:** Private (recommended) or Public
   - **Do not** add a README, .gitignore, or license (we already have them).
4. Click **Create repository**.

**Option B — Using GitHub CLI (if installed)**

```powershell
gh repo create CDSS --private --source=. --remote=origin --push --description "Clinical Decision Support System - Multi-agent AI platform for Indian hospitals"
```

If you use Option B and it runs successfully, you can skip Step 2 and Step 3.

---

## Step 2: Add the remote and push (if you used Option A)

Replace `YOUR_USERNAME` with your GitHub username (or use your org name if the repo is under an organization):

```powershell
cd d:\CDSS

# HTTPS (will prompt for username/password or token)
git remote add origin https://github.com/YOUR_USERNAME/CDSS.git

# Or SSH (if you use SSH keys)
# git remote add origin git@github.com:YOUR_USERNAME/CDSS.git

# Push the main branch (rename to main if you use main)
git branch -M main
git push -u origin main
```

If your default branch is already `master`, use:

```powershell
git push -u origin master
```

---

## Step 3: Give your team access

### If the repo is under your **personal account**

1. Open the repo on GitHub: `https://github.com/YOUR_USERNAME/CDSS`
2. Go to **Settings** → **Collaborators** (or **Collaborators and teams**).
3. Click **Add people**.
4. Enter each teammate’s GitHub username or email and choose a role:
   - **Read** — clone and pull only
   - **Write** — push branches, open/merge PRs
   - **Admin** — manage settings and access
5. They accept the invite from their email or GitHub notifications.

### If the repo is under a **GitHub Organization**

1. Repo → **Settings** → **Collaborators and teams**.
2. **Add teams** or **Invite a collaborator**.
3. Assign role (Read / Write / Admin) per team or person.

### Using GitHub CLI (optional)

```powershell
# Invite a user with write access
gh api repos/YOUR_USERNAME/CDSS/collaborators/TEAMMATE_USERNAME -X PUT -f permission=push

# Or add a team (org repos)
# Repo Settings → Manage access → Add team
```

---

## Quick reference

| Goal              | Where on GitHub                          |
|-------------------|------------------------------------------|
| Add collaborators | Repo → **Settings** → **Collaborators**  |
| Manage teams      | Repo → **Settings** → **Collaborators and teams** (org) |
| Branch protection | Repo → **Settings** → **Branches**       |

After pushing, teammates can clone with:

```powershell
git clone https://github.com/YOUR_USERNAME/CDSS.git
cd CDSS
```
