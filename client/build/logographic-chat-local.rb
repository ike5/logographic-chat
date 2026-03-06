# Temporary local formula for testing
class LogographicChat < Formula
  desc "TUI chat client for Logographic Chat"
  homepage "https://github.com/ike5/logographic-chat"
  version "0.1.0"
  license "MIT"

  url "file://#{Dir.pwd}/logographic-chat-darwin-arm64.tar.gz"
  sha256 "457ade26b67df870264843257f1ac5cbb6ebb626b33e5994ba7139cecfdbb232"

  def install
    bin.install "logographic-chat"
  end

  test do
    assert_match "Usage", shell_output("#{bin}/logographic-chat --help")
  end
end