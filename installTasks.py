# -*- coding: utf-8 -*-
# OmniTranslate - Installation & Uninstallation Tasks
# Author: Isara Watthanawirojkul

import os
import shutil
import globalVars
import logHandler


def onUninstall():
    """Cleans up downloaded models and configuration files upon add-on uninstallation,
    while preserving them during add-on updates."""
    try:
        pending_install_dir = os.path.join(globalVars.appArgs.configPath, "addons", "omni_translate.pendingInstall")
        if os.path.exists(pending_install_dir):
            logHandler.log.info("OmniTranslate: Update in progress. Preserving configuration and offline models.")
            return

        models_dir = os.path.join(globalVars.appArgs.configPath, "omni_translate_models")
        if os.path.exists(models_dir):
            shutil.rmtree(models_dir, ignore_errors=True)
            logHandler.log.info("OmniTranslate: Removed offline models directory on uninstall.")

        conf_file = os.path.join(globalVars.appArgs.configPath, "omni_translate_config.json")
        if os.path.exists(conf_file):
            try:
                os.remove(conf_file)
                logHandler.log.info("OmniTranslate: Removed config file on uninstall.")
            except Exception:
                pass
    except Exception as e:
        logHandler.log.error(f"OmniTranslate: Error during onUninstall cleanup: {e}")