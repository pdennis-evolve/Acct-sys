"""Installs the backend as a native Windows Service (via pywin32) so it
starts automatically on boot and survives logoff, without any
third-party service-wrapper executable.

Requires requirements-windows.txt to be installed (pywin32), and:
    venv\\Scripts\\python.exe -m pywin32_postinstall -install
run once after installing pywin32, per pywin32's own setup docs.

Usage (from an elevated/Administrator command prompt, with the venv's
python.exe on PATH or referenced directly):
    python windows_service.py install
    python windows_service.py start
    python windows_service.py stop
    python windows_service.py remove

See docs/WINDOWS_SERVER_INSTALL.md for the full walkthrough, including
how to set this to auto-start and run as a dedicated service account.
"""
import os
import sys
import threading

import servicemanager
import win32event
import win32service
import win32serviceutil


class EvolveBusinessSuiteService(win32serviceutil.ServiceFramework):
    _svc_name_ = "EvolveBusinessSuite"
    _svc_display_name_ = "Evolve Business Suite API"
    _svc_description_ = "Flask/waitress backend API for Evolve Business Suite."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self._waitress_server = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self._waitress_server is not None:
            self._waitress_server.close()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        self.main()

    def main(self):
        # Service processes start with an arbitrary working directory --
        # anchor to this file's directory so .env and the storage/
        # fallback (LocalDiskStorage) resolve the same way they do when
        # run manually from this folder.
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        from dotenv import load_dotenv
        load_dotenv()

        from waitress import create_server

        from app import create_app

        app = create_app()

        host = os.environ.get("WAITRESS_HOST", "127.0.0.1")
        port = int(os.environ.get("WAITRESS_PORT", "5000"))
        threads = int(os.environ.get("WAITRESS_THREADS", "8"))

        self._waitress_server = create_server(app, host=host, port=port, threads=threads)
        server_thread = threading.Thread(target=self._waitress_server.run, daemon=True)
        server_thread.start()

        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(EvolveBusinessSuiteService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(EvolveBusinessSuiteService)
