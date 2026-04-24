"""Default worker entrypoint.

We only ship one worker today (refinement), so ``python -m pr_agent.workers``
dispatches straight to it. If a second worker lands later, swap this for a
tiny argparse-based switch.
"""

from pr_agent.workers.refinement import main

if __name__ == "__main__":
    main()
