# SeaGrid in a nutshell (TL;DR for anyone)

## What is this?
A program that stands guard over Romania's "cables and pipes" in the Black Sea:
gas platforms, pipelines, internet cables on the seabed and the entrance to the port of Constanța.

It watches the ships in the area and shouts "heads up!" when one behaves suspiciously.

## What counts as "suspicious"?
- **It switches off its "public GPS" (AIS).** Every large ship broadcasts its position by radio. If it goes silent for more than 30 minutes near something important, that's suspicious.
- **It reappears where it shouldn't.** If it said it was doing 12 knots, but 2 hours later it is far too close (or too far), it did something in between.
- **It sits still where it has no business being.** A ship circling slowly above a cable is not innocently fishing.
- **It "jumps" from one place to another.** Its position moved 25 km in one minute: the signal is spoofed.

Besides ships, we also "listen" to:
- an **underwater microphone** (hydrophone), which hears low engine noise or a dragged anchor;
- the **fibre inside the cable**, which feels vibrations when someone tampers with it.

## What do you get at the end?
An **alert** with:
- a **risk score from 0 to 100**: every suspicious sign adds points, and the screen shows exactly how many and why;
- a **plain-English explanation**, such as "AIS off for 121 min, 1 km from the cable, the hydrophone heard something";
- **which patrol vessel to send** and how long it takes to get there.

## The demo story
1. The cargo ship **MV SEA FALCON** is heading for Constanța.
2. Near a gas platform and a cable, it switches its AIS off. On the map it turns grey and a growing circle appears: "it's somewhere in here".
3. After 30 minutes the first alert goes off.
4. Nearby, the fishing boat **FV NORTHERN DAWN** has been sitting still for a long time. The two ships are linked and the score rises.
5. The hydrophone hears something, the cable fibre vibrates. The score becomes **critical** and the system recommends a patrol vessel.
6. SEA FALCON reappears too close for the speed it was reporting: "too slow", so it stopped somewhere.

## Important
- **Everything is simulated.** The ships, sensors and patrol units are made up and labelled **SIMULATED**.
- **Platform and cable positions are approximate**, not official.
- **The explanations are not written by an AI.** They are fixed sentences filled in with the detector's numbers.

## How do I start it? (3 steps)
```bash
python -m devtools.bootstrap      # once: installs everything
python -m core.demo               # generates the story
python -m http.server 8000        # then open http://localhost:8000/web/ and press ▶
```

More details: [the main README](../README.md) · team rules: [AGENTS.md](../AGENTS.md)
