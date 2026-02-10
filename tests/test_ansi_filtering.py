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
    text = "Line1\nLine2\tTabbed\r\nLine3"
    assert strip_ansi_codes(text) == text


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

