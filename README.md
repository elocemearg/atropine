# Atropine
Atropine is a program written in Python which helps with running [FOCAL events](https://focalcountdown.co.uk/). It generates fixtures, takes results, works out the standings, and can display it all in a separate window suitable for showing on a public-facing screen.

# Prerequisites
To run Atropine you need to have [Python 3](https://www.python.org/downloads/) installed, unless you want to use the Windows standalone build which was introduced in Atropine 1.3.0. You can get Python from the [Python downloads page](https://www.python.org/downloads/).

You use Atropine through your web browser, but it does **not** need access to the internet to run. Atropine is its own web server which runs on your own computer, and your browser connects to that.

# Instructions for getting started
 * If Python 3 is not already installed on your computer, or if you're not sure whether it's installed, [download and install Python 3](https://www.python.org/downloads/).
 * Get Atropine. You can either:
   * Clone the git repository, or,
   * If you don't use git but have somehow found this on github, download the latest Atropine zip file from <https://greem.co.uk/atropine/>. Unzip the zip file into a new folder of your choosing. Don't move any of Atropine's files out of that folder - the location of `atropine.py` in relation to the subfolders must be maintained as it is. It's okay to make a shortcut (or symlink, on Linux) to atropine.py and put the shortcut anywhere you want.
 * Run `atropine.py`.
 * Atropine will open a small web server on your computer, and give you a link to paste into your browser, like this: `http://localhost:3960/`
 * Go to that link in your web browser. You are now using the web interface, and you can create and administer your tournament from there.

# Further documentation
The file `webroot/docs/index.html` contains further information about using Atropine.

# Licence
Atropine is free to use, and is released under the [BSD 3-clause licence](https://opensource.org/license/bsd-3-clause/).

The font files under `webroot/fonts/` are from third-party sources and are distributed with Atropine in accordance with their own licences. See `webroot/fonts/FontLicences.txt` for details.
