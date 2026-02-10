"""Tests for ANSI escape code filtering."""

import pytest
import asyncio

from pty_mcp.session import strip_ansi_codes, PTYSession
from pty_mcp.config import SessionConfig


def test_strip_ansi_codes_colors():
    """Test stripping ANSI color codes."""
    print("\n" + "="*60)
    print("=== Testing Color Code Stripping ===")
    print("="*60)
    
    # Standard colors
    text = "\x1b[31mRed text\x1b[0m"
    result = strip_ansi_codes(text)
    print(f"\nTest 1: Standard red color")
    print(f"WITH ANSI (colored): {text}")
    print(f"WITHOUT ANSI (plain): {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "Red text"
    
    # 256 colors
    text = "\x1b[38;5;196mBright red\x1b[0m"
    result = strip_ansi_codes(text)
    print(f"\nTest 2: 256-color mode")
    print(f"WITH ANSI (colored): {text}")
    print(f"WITHOUT ANSI (plain): {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "Bright red"
    
    # RGB colors
    text = "\x1b[38;2;255;0;0mRGB red\x1b[0m"
    result = strip_ansi_codes(text)
    print(f"\nTest 3: RGB color mode")
    print(f"WITH ANSI (colored): {text}")
    print(f"WITHOUT ANSI (plain): {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "RGB red"


def test_strip_ansi_codes_cursor_movement():
    """Test stripping cursor movement codes."""
    print("\n=== Testing Cursor Movement Code Stripping ===")
    text = "\x1b[2JClear\x1b[1;1HHome"
    result = strip_ansi_codes(text)
    print(f"Input:  {repr(text)}")
    print(f"Output: {repr(result)}")
    assert "Clear" in result
    assert "Home" in result
    assert "\x1b" not in result


def test_strip_ansi_codes_formatting():
    """Test stripping text formatting codes."""
    print("\n" + "="*60)
    print("=== Testing Text Formatting Code Stripping ===")
    print("="*60)
    
    # Bold, italic, underline
    text = "\x1b[1mBold\x1b[0m \x1b[3mItalic\x1b[0m \x1b[4mUnderline\x1b[0m"
    result = strip_ansi_codes(text)
    print(f"\nBold, Italic, Underline formatting:")
    print(f"WITH ANSI (formatted): {text}")
    print(f"WITHOUT ANSI (plain):  {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "Bold Italic Underline"


def test_strip_ansi_codes_complex():
    """Test stripping complex ANSI sequences."""
    print("\n" + "="*60)
    print("=== Testing Complex ANSI Sequences ===")
    print("="*60)
    
    # Multiple codes in one sequence
    text = "\x1b[1;31;42mBold red on green\x1b[0m"
    result = strip_ansi_codes(text)
    print(f"\nTest 1: Bold red text on green background")
    print(f"WITH ANSI (formatted): {text}")
    print(f"WITHOUT ANSI (plain):  {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "Bold red on green"
    
    # Mixed formatting
    text = "Normal \x1b[1mBold\x1b[0m Normal \x1b[31mRed\x1b[0m Normal"
    result = strip_ansi_codes(text)
    print(f"\nTest 2: Mixed normal and formatted text")
    print(f"WITH ANSI (formatted): {text}")
    print(f"WITHOUT ANSI (plain):  {result}")
    print(f"Repr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "Normal Bold Normal Red Normal"


def test_strip_ansi_codes_osc_sequences():
    """Test stripping OSC (Operating System Command) sequences."""
    print("\n=== Testing OSC Sequence Stripping ===")
    
    # Terminal title
    text = "\x1b]0;Terminal Title\x07Content"
    result = strip_ansi_codes(text)
    print(f"Input:  {repr(text)}")
    print(f"Output: {repr(result)}")
    assert result == "Content"
    
    # Alternative OSC terminator
    text = "\x1b]0;Title\x1b\\Content"
    result = strip_ansi_codes(text)
    print(f"Input:  {repr(text)}")
    print(f"Output: {repr(result)}")
    assert result == "Content"


def test_strip_ansi_codes_preserves_text():
    """Test that regular text is preserved."""
    text = "Hello, World! 123 $special #chars"
    assert strip_ansi_codes(text) == text


def test_strip_ansi_codes_preserves_whitespace():
    """Test that newlines, tabs, and spaces are preserved."""
    text = "Line1\nLine2\tTabbed\nLine3"
    assert strip_ansi_codes(text) == text


def test_strip_ansi_codes_normalizes_crlf():
    """Test that \\r\\n is normalized to \\n."""
    print("\n" + "="*60)
    print("=== Testing CRLF Normalization ===")
    print("="*60)
    
    text = "Line1\r\nLine2\r\nLine3\r\n"
    result = strip_ansi_codes(text)
    expected = "Line1\nLine2\nLine3\n"
    
    print(f"\nWindows-style line endings (\\r\\n):")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected


def test_strip_ansi_codes_progress_bar():
    """Test handling of progress bar with carriage returns."""
    print("\n" + "="*60)
    print("=== Testing Progress Bar Filtering ===")
    print("="*60)
    
    # Simulate a progress bar that overwrites itself
    text = "Downloading: 10%\rDownloading: 50%\rDownloading: 100%"
    result = strip_ansi_codes(text)
    expected = "Downloading: 100%"
    
    print(f"\nProgress bar with overwrites:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected


def test_strip_ansi_codes_spinner():
    """Test handling of spinner animation."""
    print("\n" + "="*60)
    print("=== Testing Spinner Filtering ===")
    print("="*60)
    
    # Simulate a spinner
    text = "Loading |...\rLoading /...\rLoading -...\rLoading \\...\rLoading Done!"
    result = strip_ansi_codes(text)
    expected = "Loading Done!"
    
    print(f"\nSpinner with overwrites:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected


def test_strip_ansi_codes_multiline_progress():
    """Test progress bar across multiple lines."""
    print("\n" + "="*60)
    print("=== Testing Multi-line Progress ===")
    print("="*60)
    
    # Progress on multiple lines with some having overwrites
    text = "File1: 10%\rFile1: 100%\nFile2: 20%\rFile2: 100%\nComplete"
    result = strip_ansi_codes(text)
    expected = "File1: 100%\nFile2: 100%\nComplete"
    
    print(f"\nMulti-line with progress:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected


def test_strip_ansi_codes_crlf_with_progress():
    """Test combined \\r\\n and standalone \\r handling."""
    print("\n" + "="*60)
    print("=== Testing Combined CRLF and Progress ===")
    print("="*60)
    
    # Mix of \r\n line endings and \r overwrites
    text = "Line1\r\nProgress: 10%\rProgress: 100%\r\nLine3\r\n"
    result = strip_ansi_codes(text)
    expected = "Line1\nProgress: 100%\nLine3\n"
    
    print(f"\nMixed line endings and progress:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected


def test_strip_ansi_codes_ansi_with_crlf():
    """Test ANSI codes with CRLF line endings."""
    print("\n" + "="*60)
    print("=== Testing ANSI Codes with CRLF ===")
    print("="*60)
    
    text = "\x1b[31mRed line\x1b[0m\r\n\x1b[32mGreen line\x1b[0m\r\n"
    result = strip_ansi_codes(text)
    expected = "Red line\nGreen line\n"
    
    print(f"\nANSI colors with Windows line endings:")
    print(f"WITH ANSI (colored):\n{text}")
    print(f"WITHOUT ANSI (plain):\n{result}")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    assert result == expected


def test_strip_ansi_codes_ansi_progress_bar():
    """Test colored progress bar with overwrites."""
    print("\n" + "="*60)
    print("=== Testing Colored Progress Bar ===")
    print("="*60)
    
    # Progress bar with ANSI colors and carriage returns
    text = "\x1b[33mProgress: 10%\x1b[0m\r\x1b[33mProgress: 50%\x1b[0m\r\x1b[32mProgress: 100%\x1b[0m"
    result = strip_ansi_codes(text)
    expected = "Progress: 100%"
    
    print(f"\nColored progress bar:")
    print(f"WITH ANSI (colored): {text}")
    print(f"WITHOUT ANSI (plain): {result}")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    assert result == expected


def test_strip_ansi_codes_trailing_cr():
    """Test handling of trailing carriage return (the bug case)."""
    print("\n" + "="*60)
    print("=== Testing Trailing CR (Bug Fix) ===")
    print("="*60)
    
    # Trailing \r should keep the text, not delete it
    text = "echo test\r"
    result = strip_ansi_codes(text)
    expected = "echo test"
    
    print(f"\nTrailing \\r:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected
    
    # Sentinel with trailing \r (critical for command detection)
    text2 = "__PTY_DONE_abc123__\r"
    result2 = strip_ansi_codes(text2)
    expected2 = "__PTY_DONE_abc123__"
    
    print(f"\nSentinel with trailing \\r:")
    print(f"Input repr:  {repr(text2)}")
    print(f"Output repr: {repr(result2)}")
    print(f"Expected:    {repr(expected2)}")
    assert result2 == expected2


def test_strip_ansi_codes_multiple_prompts():
    """Test multiple shell prompts separated by carriage returns."""
    print("\n" + "="*60)
    print("=== Testing Multiple Prompts (TCL_LEC Case) ===")
    print("="*60)
    
    # Multiple prompts like TCL_LEC> \rTCL_LEC> \rTCL_LEC>
    text = "TCL_LEC> \rTCL_LEC> \rTCL_LEC> "
    result = strip_ansi_codes(text)
    expected = "TCL_LEC> "
    
    print(f"\nMultiple prompts with \\r overwrites:")
    print(f"Input repr:  {repr(text)}")
    print(f"Output repr: {repr(result)}")
    print(f"Expected:    {repr(expected)}")
    assert result == expected
    
    # Same but without trailing space
    text2 = "PROMPT> \rPROMPT> \rPROMPT>"
    result2 = strip_ansi_codes(text2)
    expected2 = "PROMPT>"
    
    print(f"\nWithout trailing space:")
    print(f"Input repr:  {repr(text2)}")
    print(f"Output repr: {repr(result2)}")
    print(f"Expected:    {repr(expected2)}")
    assert result2 == expected2


def test_strip_ansi_codes_multiple_consecutive_cr():
    """Test multiple consecutive carriage returns."""
    print("\n" + "="*60)
    print("=== Testing Multiple Consecutive CR ===")
    print("="*60)
    
    # Multiple trailing \r\r
    text1 = "PROMPT> \r\r"
    result1 = strip_ansi_codes(text1)
    expected1 = "PROMPT> "
    
    print(f"\nDouble trailing \\r\\r:")
    print(f"Input repr:  {repr(text1)}")
    print(f"Output repr: {repr(result1)}")
    print(f"Expected:    {repr(expected1)}")
    assert result1 == expected1
    
    # Progress with multiple \r at end
    text2 = "something\rPROMPT> \r\r"
    result2 = strip_ansi_codes(text2)
    expected2 = "PROMPT> "
    
    print(f"\nOverwrites then multiple \\r:")
    print(f"Input repr:  {repr(text2)}")
    print(f"Output repr: {repr(result2)}")
    print(f"Expected:    {repr(expected2)}")
    assert result2 == expected2
    
    # Many \r at the end
    text3 = "text1\rtext2\rtext3\r\r\r"
    result3 = strip_ansi_codes(text3)
    expected3 = "text3"
    
    print(f"\nMany trailing \\r:")
    print(f"Input repr:  {repr(text3)}")
    print(f"Output repr: {repr(result3)}")
    print(f"Expected:    {repr(expected3)}")
    assert result3 == expected3
    
    # Starting with \r
    text4 = "\rPROMPT> "
    result4 = strip_ansi_codes(text4)
    expected4 = "PROMPT> "
    
    print(f"\nStarting with \\r:")
    print(f"Input repr:  {repr(text4)}")
    print(f"Output repr: {repr(result4)}")
    print(f"Expected:    {repr(expected4)}")
    assert result4 == expected4


def test_strip_ansi_codes_removes_control_chars():
    """Test that other control characters are removed."""
    print("\n=== Testing Control Character Removal ===")
    # Bell, backspace, form feed, etc.
    text = "Text\x07with\x08control\x0cchars"
    result = strip_ansi_codes(text)
    print(f"Input:  {repr(text)}")
    print(f"Output: {repr(result)}")
    assert result == "Textwithcontrolchars"


def test_strip_ansi_codes_empty_string():
    """Test with empty string."""
    assert strip_ansi_codes("") == ""


def test_strip_ansi_codes_only_ansi():
    """Test string with only ANSI codes."""
    text = "\x1b[31m\x1b[1m\x1b[0m"
    assert strip_ansi_codes(text) == ""


@pytest.mark.asyncio
async def test_session_filters_colored_output():
    """Test that PTY session filters ANSI codes from actual command output."""
    print("\n=== Testing PTY Session with ls --color ===")
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="test_ansi", config=config)
    
    await session.start()
    await asyncio.sleep(0.2)
    
    # Use ls --color to generate ANSI colored output
    # Even if directory is empty, ls should not output ANSI codes
    output, completed = await session.run_command("ls --color=always", timeout=5.0)
    
    print(f"Command: ls --color=always")
    print(f"Completed: {completed}")
    print(f"Output contains ANSI codes: {'\\x1b[' in output or '\\x1b]' in output}")
    print(f"First 200 chars of output: {repr(output[:200])}")
    
    assert completed
    # Output should not contain ANSI escape sequences
    assert "\x1b[" not in output
    assert "\x1b]" not in output
    
    await session.stop()


@pytest.mark.asyncio
async def test_session_filters_color_commands():
    """Test filtering with commands that explicitly use colors."""
    print("\n=== Testing PTY Session with printf Colors ===")
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="test_color_cmd", config=config)
    
    await session.start()
    await asyncio.sleep(0.2)
    
    # Use printf to generate colored output explicitly
    cmd = r"printf '\033[31mRed\033[0m Text'"
    output, completed = await session.run_command(cmd, timeout=5.0)
    
    print(f"Command: {cmd}")
    print(f"Completed: {completed}")
    print(f"Output: {repr(output)}")
    print(f"Contains 'Red': {'Red' in output}")
    print(f"Contains 'Text': {'Text' in output}")
    print(f"Contains ANSI codes: {'\\x1b' in output}")
    
    assert completed
    assert "Red" in output
    assert "Text" in output
    # Should not contain escape sequences
    assert "\x1b" not in output
    assert "033" not in output or "\\033" in output  # Literal string is ok
    
    await session.stop()


@pytest.mark.asyncio
async def test_buffer_contains_filtered_output():
    """Test that buffer contains ANSI-filtered output."""
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="test_buffer_filter", config=config)
    
    await session.start()
    await asyncio.sleep(0.2)
    
    # Generate colored output
    cmd = r"printf '\033[1;32mSuccess!\033[0m'"
    await session.run_command(cmd, timeout=5.0)
    
    buffer = session.get_buffer()
    assert "Success!" in buffer
    # Buffer should not contain ANSI codes
    assert "\x1b" not in buffer
    
    await session.stop()


def test_strip_ansi_charset_sequences():
    """Test stripping charset selection sequences."""
    text = "\x1b(BNormal\x1b)0Graphics"
    result = strip_ansi_codes(text)
    assert "Normal" in result
    assert "Graphics" in result
    assert "\x1b" not in result


def test_strip_ansi_real_world_prompt():
    """Test with real-world bash prompt containing colors."""
    print("\n" + "="*60)
    print("=== Testing Real-World Colored Bash Prompt ===")
    print("="*60)
    
    # Typical colored bash prompt
    prompt = "\x1b[01;32muser@host\x1b[00m:\x1b[01;34m/path\x1b[00m$ "
    result = strip_ansi_codes(prompt)
    print(f"\nTypical bash prompt with colors:")
    print(f"WITH ANSI (colored):  {prompt}")
    print(f"WITHOUT ANSI (plain): {result}")
    print(f"Repr of input:  {repr(prompt)}")
    print(f"Repr of output: {repr(result)}")
    assert result == "user@host:/path$ "


def test_strip_ansi_multiline_with_codes():
    """Test multiline text with ANSI codes."""
    print("\n" + "="*60)
    print("=== Testing Multiline Text with ANSI Codes ===")
    print("="*60)
    
    text = (
        "\x1b[1mLine 1 Bold\x1b[0m\n"
        "\x1b[31mLine 2 Red\x1b[0m\n"
        "Line 3 Normal"
    )
    result = strip_ansi_codes(text)
    expected = "Line 1 Bold\nLine 2 Red\nLine 3 Normal"
    
    print(f"\nMultiline text with formatting:")
    print("WITH ANSI (formatted):")
    print(text)
    print("\nWITHOUT ANSI (plain):")
    print(result)
    print(f"\nRepr of input:  {repr(text)}")
    print(f"Repr of output: {repr(result)}")
    assert result == expected


@pytest.mark.asyncio
async def test_session_with_grep_color():
    """Test that grep --color output is properly filtered."""
    print("\n=== Testing PTY Session with grep --color ===")
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="test_grep", config=config)
    
    await session.start()
    await asyncio.sleep(0.2)
    
    # Create a temp file and grep it with color
    cmd = "echo 'test line' | grep --color=always 'test'"
    output, completed = await session.run_command(cmd, timeout=5.0)
    
    print(f"Command: {cmd}")
    print(f"Completed: {completed}")
    print(f"Output: {repr(output)}")
    print(f"Contains ANSI codes: {'\\x1b' in output}")
    
    assert completed
    assert "test" in output
    assert "line" in output
    # Should not contain ANSI codes
    assert "\x1b" not in output
    
    await session.stop()


@pytest.mark.asyncio
async def test_session_with_complex_colors():
    """Test with complex colored output."""
    print("\n=== Testing PTY Session with Complex Color Combinations ===")
    config = SessionConfig(command="/bin/bash")
    session = PTYSession(session_id="test_complex", config=config)
    
    await session.start()
    await asyncio.sleep(0.2)
    
    # Test with printf producing various color combinations
    commands = [
        (r"printf '\033[31mRed\033[0m'", "Red"),
        (r"printf '\033[1;32mBold Green\033[0m'", "Bold Green"),
        (r"printf '\033[4;34mUnderlined Blue\033[0m'", "Underlined Blue"),
        (r"printf '\033[1;31;42mBold Red on Green\033[0m'", "Bold Red on Green"),
    ]
    
    for cmd, expected in commands:
        output, completed = await session.run_command(cmd, timeout=5.0)
        print(f"Command: {cmd}")
        print(f"Expected text: {expected}")
        print(f"Output: {repr(output)}")
        print(f"Contains ANSI codes: {'\\x1b' in output}")
        assert completed
        # Should not contain escape sequences
        assert "\x1b" not in output
    
    await session.stop()

