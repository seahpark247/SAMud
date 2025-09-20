# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a San Antonio-themed MUD (Multiuser Dungeon) project that implements a telnet-accessible text-based game server. The project is currently in initial development phase.

## Project Requirements

### Core Functionality
- Telnet server running on port 2323
- User authentication (signup/login) with SQLite persistence
- Multiuser real-time interaction in shared rooms
- Room-based and global chat systems
- Player state persistence (current room location)

### World Structure
The MUD world consists of San Antonio-themed rooms:
- The Alamo Plaza (starting location)
- River Walk North
- River Walk South
- The Pearl
- Tower of the Americas
- Mission San Jose
- Southtown

### Essential Commands
- `look` - Room description, exits, and players present
- `say <message>` - Room chat
- `shout <message>` - Global chat
- `move <exit>` or directional shortcuts (`n`, `s`, `e`, `w`) - Movement
- `who` - List online players
- `where` - Current location
- `help` - Command list
- `quit` - Save and disconnect

## Technical Architecture

### Database Schema
- Player accounts with authentication
- Player state (current room)
- Room definitions and connections
- Chat history (optional)

### Server Architecture
- Telnet connection handling
- Session management for multiple concurrent players
- Real-time message broadcasting to rooms
- Command parsing and execution system
- SQLite database integration

### Stretch Goals
- NPCs with basic AI responses
- Tick system for NPC movement
- Item system (get/drop)
- Private messaging (whisper)
- Emote system

## Development Notes

This project should be implemented as a single-process server that can handle multiple concurrent telnet connections. The architecture should support:
- Session isolation per connected player
- Real-time message broadcasting within rooms
- Persistent state management via SQLite
- Clean command parsing and response system