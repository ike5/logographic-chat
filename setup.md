Great — you’re very close. The main thing that’s changed in the Homebrew docs is that:
• Formulas (like yours) go into a tap.
• Casks are for GUI apps (.app bundles, DMGs, PKGs).
Your app is a CLI binary, so you want a Formula, not a Cask.

You should follow the Formula + Tap flow here:
👉 https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap

Below is the correct modern way to structure this in 2026.

⸻

✅ 1. Release Artifacts (Very Important)

Right now your formula expects:

logographic-chat-darwin-arm64.tar.gz

But PyInstaller gives you a raw binary:

dist/logographic-chat

Homebrew expects a tarball containing the binary.

So in CI, after building, you should:

# macOS arm64

tar -czf logographic-chat-darwin-arm64.tar.gz logographic-chat

# macOS x86_64

tar -czf logographic-chat-darwin-x86_64.tar.gz logographic-chat

# Linux

tar -czf logographic-chat-linux-x86_64.tar.gz logographic-chat

Upload those .tar.gz files as GitHub Release assets.

⸻

✅ 2. Get SHA256 Hashes

After uploading, compute the SHA:

shasum -a 256 logographic-chat-darwin-arm64.tar.gz

Put that value into your formula.

You must have real SHA256 values or Homebrew will refuse it.

⸻

✅ 3. Correct Tap Structure (Modern Layout)

Your tap repo must be:

github.com/ike5/homebrew-logographic-chat

And structured like:

homebrew-logographic-chat/
└── Formula/
└── logographic-chat.rb

NOT inside client/build/.

⸻

✅ 4. Updated Formula (Cleaned + Modernized)

Here’s a production-ready version:

class LogographicChat < Formula
desc "TUI chat client for Logographic Chat"
homepage "https://github.com/ike5/logographic-chat"
version "0.1.0"
license "MIT"

on_macos do
if Hardware::CPU.arm?
url "https://github.com/ike5/logographic-chat/releases/download/v0.1.0/logographic-chat-darwin-arm64.tar.gz"
sha256 "REAL_SHA256_HERE"
else
url "https://github.com/ike5/logographic-chat/releases/download/v0.1.0/logographic-chat-darwin-x86_64.tar.gz"
sha256 "REAL_SHA256_HERE"
end
end

on_linux do
url "https://github.com/ike5/logographic-chat/releases/download/v0.1.0/logographic-chat-linux-x86_64.tar.gz"
sha256 "REAL_SHA256_HERE"
end

def install
bin.install "logographic-chat"
end

test do
assert_match "Usage", shell_output("#{bin}/logographic-chat --help")
end
end

Why I changed the test:

Homebrew runs this in a sandbox.
Your test should not require network access.

--help is safe.

⸻

✅ 5. Tap and Install Locally (Test Before Public)

brew tap ike5/logographic-chat
brew install logographic-chat

If you’re developing locally:

brew install --build-from-source ./Formula/logographic-chat.rb

Or:

brew audit --strict --new-formula logographic-chat

You should fix any audit warnings before publishing.

⸻

✅ 6. You Do NOT Want a Cask

The page you linked is for Casks:
• Used for .app
• Used for DMG installers
• Used for GUI apps

You built a CLI binary with PyInstaller.
That belongs in a Formula, not a Cask.

⸻

🚀 Optional: Even Cleaner Approach (Recommended)

Since you’re already building with PyInstaller, you might consider:

Instead of distributing prebuilt binaries, let Homebrew:
• depends_on "python@3.12"
• install via virtualenv_install_with_resources

That’s more “Homebrew-native”.

BUT…

For a TUI app where you want:
• No Python dependency
• Fast install
• Simple UX

Your current binary distribution approach is totally fine.

⸻

🔥 Production-Ready Flow Summary
1. CI builds 3 binaries
2. CI wraps each in tar.gz
3. CI computes SHA256
4. CI updates formula automatically (optional but pro move)
5. Push to:

ike5/homebrew-logographic-chat

	6.	Users install via:

brew tap ike5/logographic-chat
brew install logographic-chat

⸻

If you’d like, I can:
• Show you a GitHub Actions workflow that auto-builds + updates SHA
• Help you decide whether to convert to a Python-based formula instead
• Help you get it into homebrew-core (harder, but possible)

Given you’re building a Django-backed TUI chat system, distributing a zero-dependency binary via Homebrew is actually a
very strong move.