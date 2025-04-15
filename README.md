# cis-benchmark-download
Python scripts to access and download benchmark documentation in different formats from the CIS (Center for Internet Securtiy) portal.

You need a licence file from the CIS download portal. Put the `license.xml` into the root of the checked out repo.

# Setup

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install requests
```

# Run

```
$ python cis_access.py --getbenchmarks
```

