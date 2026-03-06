# Formula/logographic-chat.rb
class LogographicChat < Formula
  desc "TUI chat client for Logographic Chat"
  homepage "https://github.com/ike5/logographic-chat"
  version "VERSION_PLACEHOLDER"
  license "MIT"

  on_macos do
    url "https://github.com/ike5/logographic-chat/releases/download/vTAG_PLACEHOLDER/logographic-chat-darwin-arm64.tar.gz"
    sha256 "SHA256_ARM64_PLACEHOLDER"
  end

  on_linux do
    url "https://github.com/ike5/logographic-chat/releases/download/vTAG_PLACEHOLDER/logographic-chat-linux-x86_64.tar.gz"
    sha256 "SHA256_LINUX_PLACEHOLDER"
  end

  def install
    bin.install "logographic-chat"
  end

  test do
    assert_match "Usage", shell_output("#{bin}/logographic-chat --help")
  end
end
