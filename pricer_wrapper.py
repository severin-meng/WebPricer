import subprocess, json, threading, queue

class CppPricer:
    def __init__(self, executable="./pricer_service"):
        # Start C++ pricer once
        self.proc = subprocess.Popen(
            [executable],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.q = queue.Queue()
        # Thread continuously listens for C++ outputs
        self.listener = threading.Thread(target=self._listen, daemon=True)
        self.listener.start()

    def _listen(self):
        for line in self.proc.stdout:  # read JSON from C++
            self.q.put(json.loads(line.strip()))

    def query(self, data: dict) -> dict:
        """Send JSON to C++ pricer and return response"""
        self.proc.stdin.write(json.dumps(data) + "\n")
        self.proc.stdin.flush()
        return self.q.get()

    def stop(self):
        self.proc.stdin.write("quit\n")
        self.proc.stdin.flush()
        self.proc.terminate()