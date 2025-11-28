# Changelog

## [1.3.1] - 2025-11-28

- Fixed missing sound effects in the game
- Added pygame.mixer initialization and sound loading system
- Implemented paddle bounce sound effect (bounce.wav)
- Added random brick hit sound effects (Jump1.wav, Jump2.wav, Jump3.wav)
- Added background music (S31-Night Prowler.ogg)
- Updated version to 1.3.1

## [1.3.0] - 2025-11-28

- Fixed code error with multiple main() calls
- Added sound system with background music, paddle bounce sound, and brick hit sounds using pygame.mixer

## [1.2.0] - 2025-11-28

- Clear ball trail when pausing after losing a life to avoid duplicate ball display
- Add different beep sounds for brick hits based on row color using winsound

## [1.1.0] - 2025-11-28

- Added restart functionality with R key after game end
- Pause and show start hint after losing a life
- Colored paddle sections (red left, white middle, blue right) for bounce direction indication
- Added fading trail behind the ball
- Added comprehensive comments throughout the code

## [1.0.0] - 2025-11-28

- Initial version with basic Arkanoid gameplay
- Added start screen with hint to press arrows
- Game over screen stays open instead of auto-closing
- Ball starts on paddle and bounces on first movement