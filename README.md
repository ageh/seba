# Space Engineers Blueprint Analyzer (seba)

This is a simple script that analyzes a blueprint and outputs how many of each component you need to build it. Total amounts of ingots or ores needed are also displayed, respectively.

## Requirements

Python with [Click](https://pypi.org/project/click/) and [lxml](https://pypi.org/project/lxml/) packages installed. Tested on Python 3.9.1, no guarantees for this to work on older Python3 versions.

## Usage

To analyze a blueprint simply call the script with the path to blueprint file. You can find your blueprints in

_C:\Users\<YOUR USER NAME HERE>\AppData\Roaming\SpaceEngineers\Blueprints\local_

Then simply call the script

    python se_blueprint_analyzer.py blueprint.sbc

and you should see the output. If your game is not installed in the standard location you can pass the `-s` flag to the script to set the `steamapps` folder where Space Engineers is installed in. For example

    python se_blueprint_analyzer.py blueprint.sbc -s D:/steamapps

if your `steamapps` folder is `D:\steamapps` instead of the default `C:\Program Files (x86)\Steam\steamapps`.

Per default the database containing the info for the blocks is cached and the game files are only parsed when the cached info does not exist yet, e.g. on the first run of the script. However you can force the database to rebuild by passing the `-r` flag. Simply call

    python -r se_blueprint_analyzer.py blueprint.sbc

(and optionally with the `steamapps` folder changed) and it will parse the game files again. This is useful if there was a new update introducing new blocks. If the script encounters a block in the blueprint that is not contained in the cache it will automatically attempt to parse the game files located at the given `steamapps` folder.

