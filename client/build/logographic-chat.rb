# Template used by .github/workflows/release.yml
# Placeholders are replaced by CI during release — do not fill them in manually.
class LogographicChat < Formula
  desc "TUI chat client for Logographic Chat"
  homepage "https://github.com/ike5/logographic-chat"
  version "VERSION_PLACEHOLDER"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/ike5/logographic-chat/releases/download/TAG_PLACEHOLDER/logographic-chat-darwin-arm64.tar.gz"
      sha256 "SHA256_ARM64_PLACEHOLDER"
    else
      url "https://github.com/ike5/logographic-chat/releases/download/TAG_PLACEHOLDER/logographic-chat-darwin-x86_64.tar.gz"
      sha256 "SHA256_X86_64_PLACEHOLDER"
    end
  end

  on_linux do
    url "https://github.com/ike5/logographic-chat/releases/download/TAG_PLACEHOLDER/logographic-chat-linux-x86_64.tar.gz"
    sha256 "SHA256_LINUX_PLACEHOLDER"
  end

  def install
    bin.install "logographic-chat"
  end

  test do
    assert_match "Usage", shell_output("#{bin}/logographic-chat --help")
  end
end
