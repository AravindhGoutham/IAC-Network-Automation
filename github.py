#!/usr/bin/env python3

import os
import git
from git import Repo
import getpass

def init_repo(repo_dir):
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)
    try:
        repo = Repo(repo_dir)
        if not repo.bare:
            print(f"Repository already initialized at {repo_dir}")
        else:
            print("Initializing repository")
            repo = Repo.init(repo_dir)
    except git.exc.InvalidGitRepositoryError:
        print("Initializing repository")
        repo = Repo.init(repo_dir)
    return repo

def create_initial_commit(repo):
    if repo.head.is_valid() is False:
        with open(os.path.join(repo.working_tree_dir, 'README.md'), 'w') as f:
            f.write("# ADA-Robocorp\n")
        repo.index.add(['README.md'])
        repo.index.commit("Initial commit")
        print("Initial commit created.")

def commit_changes(repo, commit_message):
    repo.git.add(A=True)
    repo.index.commit(commit_message)
    print("Changes committed successfully.")

def push_changes(repo, branch='main', username=None, token=None, github_url=None):
    origin = repo.remotes.origin
    origin.set_url(f"https://{username}:{token}@{github_url.replace('https://', '')}")

    if branch not in repo.heads:
        print(f"Branch '{branch}' does not exist locally. Creating it now.")
        repo.git.checkout("-b", branch)

    repo.git.push("--set-upstream", "origin", branch)
    print(f"Changes pushed to the '{branch}' branch of GitHub.")

def main():
    repo_dir = os.path.expanduser("~/iac-netman")
    github_url = "https://github.com/AravindhGoutham/IAC-Network-Automation.git"
    username = "AravindhGoutham"
    token = getpass.getpass("Enter your GitHub personal access token (hidden): ")
    branch = "main"

    repo = init_repo(repo_dir)

    if not repo.remotes:
        print(f"Adding remote GitHub repository: {github_url}")
        repo.create_remote('origin', github_url)

    create_initial_commit(repo)

    try:
        commit_changes(repo, "Initial commit or update")
    except Exception as e:
        print(f"No changes to commit: {e}")

    push_changes(repo, branch, username, token, github_url)

if __name__ == "__main__":
    main()
