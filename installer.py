# THIS IS JUST THE SOURCE FOR IT, IT REQUIRES PYTHON AND A BUNCH OF THINGS, INSTEAD, USE THE STANDALONE EXECUTABLE IN "Releases".

import sys
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, 
    QLabel, QRadioButton, QButtonGroup, QProgressBar, 
    QTextEdit, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal

class InstallWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool)

    def __init__(self, branch):
        super().__init__()
        self.branch = branch

    def run_command(self, cmd):
        """Runs a command and streams its live output to the wizard log."""
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            clean_line = line.strip()
            if clean_line:
                self.log_signal.emit(clean_line)
        process.wait()
        return process.returncode

    def run(self):
        steps = [
            (
                "Adding Cordial Flatpak repository...",
                "flatpak remote-add --user --if-not-exists --no-gpg-verify cordial https://luohoa97.github.io/cordial/repo"
            ),
            (
                f"Installing Cordial ({self.branch} branch)...",
                f"flatpak install --user -y --or-update cordial io.github.luohoa97.Cordial//{self.branch}"
            )
        ]

        total = len(steps)
        for index, (label, cmd) in enumerate(steps):
            self.log_signal.emit(f"\n▶ {label}")
            code = self.run_command(cmd)
            
            if code != 0:
                self.log_signal.emit(f"\n❌ Installation failed (exit code {code}).")
                self.finished_signal.emit(False)
                return

            self.progress_signal.emit(int(((index + 1) / total) * 100))

        self.log_signal.emit("\n✔ Cordial has been installed successfully!")
        self.finished_signal.emit(True)


# --- WIZARD PAGES ---

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Easy Cordial")
        self.setSubTitle("Cordial Flatpak Setup Wizard")
        
        layout = QVBoxLayout()
        label = QLabel(
            "This wizard will add the Cordial Flatpak repository and install Cordial on your system.\n\n"
            "Click 'Next' to select your preferred release channel."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)


class BranchPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Select Release Channel")
        self.setSubTitle("Choose which version of Cordial to install")

        layout = QVBoxLayout()
        
        self.master_radio = QRadioButton("Master (Default — Latest features and updates)")
        self.stable_radio = QRadioButton("Stable (Tested release)")
        self.master_radio.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.master_radio)
        self.group.addButton(self.stable_radio)

        layout.addWidget(self.master_radio)
        layout.addWidget(self.stable_radio)
        self.setLayout(layout)

    def selected_branch(self):
        return "master" if self.master_radio.isChecked() else "stable"


class InstallPage(QWizardPage):
    def __init__(self, branch_page):
        super().__init__()
        self.branch_page = branch_page
        self.setTitle("Installing Cordial")
        self.setSubTitle("Downloading and installing via Flatpak...")
        self.install_complete = False

        layout = QVBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        
        layout.addWidget(self.progress)
        layout.addWidget(self.log_box)
        self.setLayout(layout)

    def initializePage(self):
        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(False)
        branch = self.branch_page.selected_branch()
        self.setSubTitle(f"Installing Cordial ({branch}) via Flatpak...")
        
        self.worker = InstallWorker(branch)
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success):
        self.install_complete = success
        self.completeChanged.emit()

    def isComplete(self):
        return self.install_complete


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installation Complete")
        self.setSubTitle("Cordial is ready to launch")

        layout = QVBoxLayout()
        label = QLabel("Easy Cordial has finished setting up Cordial.\n")
        self.launch_cb = QCheckBox("Launch Cordial now")
        self.launch_cb.setChecked(True)

        layout.addWidget(label)
        layout.addWidget(self.launch_cb)
        self.setLayout(layout)


# --- MAIN APP ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    wizard = QWizard()
    wizard.setWindowTitle("Easy Cordial Installer")
    wizard.setWizardStyle(QWizard.WizardStyle.ModernStyle)
    wizard.resize(580, 400)

    welcome = WelcomePage()
    branch_page = BranchPage()
    install = InstallPage(branch_page)
    finish = FinishPage()

    wizard.addPage(welcome)
    wizard.addPage(branch_page)
    wizard.addPage(install)
    wizard.addPage(finish)

    # Launch Cordial when user clicks Finish if checkbox is ticked
    def on_wizard_finished(result):
        if result == QWizard.DialogCode.Accepted and finish.launch_cb.isChecked():
            subprocess.Popen(["flatpak", "run", "io.github.luohoa97.Cordial"])

    wizard.finished.connect(on_wizard_finished)
    wizard.show()
    sys.exit(app.exec())
