=========================================================
Python parser for Interactive Brokers Flex XML statements
=========================================================

.. warning::

   **This project is archived and unmaintained.** It is here for reference and
   for the git history of its bug fixes and test suite.

   Upstream `csingley/ibflex <https://github.com/csingley/ibflex>`_ resumed
   releases in 2026 (current: ``ibflex`` 1.2) and now covers most of what this
   fork was created for. **Use upstream instead:**

   .. code::

       pip uninstall ibflex2
       pip install ibflex

   Do not install both: this package and upstream both provide the ``ibflex``
   module, so the second install silently overwrites the first.

.. note::

   ``ibflex2`` 1.0.1 (2026-11-15) is the final release. ``ibflex2`` 1.0.0 had a
   client bug: the Flex Web Service client retried forever when IBKR returned a
   non-2xx HTTP response. That is fixed in 1.0.1 — pin ``ibflex2==1.0.1`` if
   you must stay on this package, or use upstream's ``client.download``.

----

``ibflex2`` converted Interactive Brokers Flex XML brokerage statement data
into typed Python objects, so it could be processed and analyzed in scripts,
notebooks, and pipelines. The sections below describe what the code in this
repository does, not a package you should adopt today.

*This module is for reading IBKR brokerage reports — it does not place
trades.*

Supports Python 3.9-3.13. The parser has no required dependency beyond
`defusedxml <https://pypi.org/project/defusedxml/>`_; the optional
``client`` for fetching Flex statements depends on
`requests <https://pypi.org/project/requests/>`_ (install ``ibflex2[web]``).

Why this fork
=============

* Parses the **current** IBKR Flex XML format. Many fields and several whole
  sections (e.g. ``StockGrantActivity``) added since 2021.
* Opt-in **unknown-attribute tolerance** so brand-new IBKR fields don't
  raise. See `Tolerance`_ below.
* **Security**: parses XML through ``defusedxml`` to guard against XXE,
  billion-laughs, and external-entity attacks.
* **Maintained tooling**: ``pyproject.toml``, ``ruff``, ``mypy``,
  ``pytest`` matrix on Linux/macOS/Windows × Python 3.9-3.13. Coverage gate
  at 95% (currently 100% on every module except ``utils.py``).
* **Schema-drift CI**: a weekly job scrapes the IBKR Activity Flex Query
  Reference and opens a tracking issue when fields appear that aren't
  declared in ``ibflex.Types``.

If the original ``csingley/ibflex`` package resumes releases, this fork
will be retired. See `CHANGELOG.md <CHANGELOG.md>`_ for what's changed.

Installation
============
::

    pip install ibflex2          # parser only
    pip install ibflex2[web]     # parser + flexget download client


Flex Parser
===========
``ibflex.parser`` parses Flex-format XML data into a hierarchy of Python
objects whose structure matches the original Flex statements, with values
converted to Python types (``datetime.datetime``, ``decimal.Decimal``, etc.)

.. code:: python

    from ibflex import parser

    response = parser.parse("2025-01_ibkr.xml")
    # or:
    response = parser.parse(xml_bytes)

    statement = response.FlexStatements[0]
    for trade in statement.Trades:
        print(f"{trade.tradeDate} {trade.buySell.name} "
              f"{abs(trade.quantity)} {trade.symbol} @ {trade.tradePrice} "
              f"{trade.currency}")

Every Flex section is exposed as a ``Tuple`` of dataclass instances, e.g.
``statement.OpenPositions``, ``statement.CashTransactions``,
``statement.Trades``. See ``ibflex/Types.py`` for every field on every
dataclass.

Tolerance
=========
IBKR adds new attributes to existing Flex sections regularly. To avoid
``FlexParserError`` when a brand-new attribute appears in your reports,
opt into tolerance mode:

.. code:: python

    from ibflex import parser

    # Process-wide:
    parser.enable_unknown_attribute_tolerance()
    response = parser.parse("recent_report.xml")
    parser.disable_unknown_attribute_tolerance()

    # Or scope-limited (recommended):
    with parser.unknown_attribute_tolerance():
        response = parser.parse("recent_report.xml")

Unknown attributes and unknown element types are silently skipped. Known
attributes still parse normally. The flag is module-global and **not
thread-safe**; use a single tolerance setting per process or guard with
locking if needed.

If you find an unknown attribute that should be recognized, please open a
new-field issue with the IBKR field name and an example XML snippet.

Flex report configuration
=========================
Configure Flex statements through `Interactive Brokers account management
<https://gdcdyn.interactivebrokers.com/sso/Login>`_:
Reports > Flex Queries > Custom Flex Queries > Configure.

You can configure whatever you like and ``ibflex2`` should parse it, with
these caveats:

* Use ISO-8601 date format (``yyyy-MM-dd``) or the default ``yyyyMMdd``.
  European-style ``dd/MM/yyyy`` is not supported.
* Use a delimiter between dates and times. The default semicolon is fastest
  to process.
* For Trades, do **not** select the top options "Symbol Summary",
  "Asset Class", or "Orders". (You can check the "Asset Class" box further
  down in the XML attribute list — that's fine.)


Flex Client
===========
Once you've defined Flex queries, you can generate an access token under
Reports > Settings > FlexWeb Service. With the token and the query ID
you can download statements over HTTP:

.. code:: python

    from ibflex import client, parser

    statement_xml = client.download(token="111111111111111111111111",
                                    query_id="111111")
    response = parser.parse(statement_xml)

You can also run the bundled ``flexget`` script::

    flexget -t 111111111111111111111111 -q 111111 > 2025-01_ibkr.xml

The client retries on transient ``Server busy`` (5 s backoff) and
``Throttled`` (10 s backoff) responses, and raises
``StatementGenerationTimeout`` after ``max_tries`` (default 5).

Development
===========

With Nix (matches CI exactly)::

    nix develop
    pytest --cov=ibflex --cov-fail-under=95 tests/
    mypy ibflex tests
    ruff check ibflex tests

Without Nix::

    pip install -e .[web,dev]
    pytest tests/
    mypy ibflex tests
    ruff check ibflex tests

See `CONTRIBUTING.md <CONTRIBUTING.md>`_ for the new-field workflow,
fixture conventions, and release process.


Resources
=========
* IBKR `Activity Flex Query Reference
  <https://www.interactivebrokers.com/en/software/reportguide/reportguide.htm>`_
* IBKR `FlexWeb Service Reference
  <https://www.interactivebrokers.com/en/software/am/am/reports/flex_web_service_version_3.htm>`_
* `capgains <https://github.com/csingley/capgains>`_ — calculates realized
  gains using ibflex
* `ib-flex-analyzer <https://github.com/wesm/ib-flex-analyzer>`_ — analyze
  Flex reports with pandas
