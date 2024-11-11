edX Student Notes API |build-status|
####################################

This is a backend store for edX Student Notes.

Overview
********

The edX Notes API is designed to be compatible with the `Annotator <http://annotatorjs.org/>`__.

Getting Started
***************

1. Install `ElasticSearch 8.15.3 <https://www.elastic.co/downloads/past-releases/elasticsearch-8-15-3>`__.

2. Install the requirements:

   .. code-block:: bash

      make develop

3. Create Elasticsearch Index and Mapping

   .. code-block:: bash

      make create-index

4. Run the Server

   .. code-block:: bash

      make run

Configuration
*************

``CLIENT_ID`` - OAuth2 Client ID, which is to be found in ``aud`` field of IDTokens which authorize users

``CLIENT_SECRET`` - secret with which IDTokens should be encoded

``ES_DISABLED`` - set to True when you need to run the service without ElasticSearch support.
                  e.g if it became corrupted and you're rebuilding the index, while still serving users
                  through MySQL

``ELASTICSEARCH_DSL['default']['hosts']`` - Your ElasticSearch host

Running Tests
*************

The ``Makefile`` provides a convenient ``validate`` command to install test dependencies, run tests, and perform linting.

.. code-block:: bash

   make validate

Running Django CI Tests Locally
*******************************

1. **Starting MySQL and Elasticsearch Services with Docker**

   Run the following commands to start the MySQL and Elasticsearch containers:

   .. code-block:: bash

      docker run -d --name mysql -p 3306:3306 \
        -e MYSQL_ROOT_PASSWORD= \
        -e MYSQL_ALLOW_EMPTY_PASSWORD=yes \
        -e MYSQL_DATABASE=edx_notes_api \
        --health-cmd="mysqladmin ping -h localhost" \
        --health-interval=10s \
        --health-timeout=5s \
        --health-retries=3 \
        mysql:8.0

   .. code-block:: bash

      docker run -d --name elasticsearch -p 9200:9200 \
         -e "discovery.type=single-node" \
         -e "bootstrap.memory_lock=true" \
         -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
         -e "xpack.security.enabled=false" \
         --health-cmd="curl -f http://localhost:9200 || exit 1" \
         --health-interval=10s \
         --health-timeout=5s \
         --health-retries=3 \
         elasticsearch:8.15.3


2. **Running Tests with Tox**

   Use `tox` to run the tests, specifying each environment to test:

   .. code-block:: bash

      tox -e django42
      tox -e quality
      tox -e pii_check
      tox -e check_keywords

   Activate the relevant Python version environment before running each command, if needed.

3. **Stopping Docker Services (Optional)**

   After testing, you can stop and remove the Docker containers to free up resources:

   .. code-block:: bash

      docker stop mysql elasticsearch
      docker rm mysql elasticsearch

How to Resync the Index
***********************

If needed, you can resync the Elasticsearch index using Django's Elasticsearch DSL management commands.

Example:

.. code-block:: bash

   python manage.py search_index --rebuild -f

For more details, refer to the `Django Elasticsearch DSL documentation <https://django-elasticsearch-dsl.readthedocs.io/en/latest/management.html>`__.

License
*******

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How To Contribute
*****************

Contributions are very welcome.

Please read `How To Contribute <https://openedx.atlassian.net/wiki/spaces/COMM/pages/941457737/How+to+Start+Contributing+Code>`_ for details.

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@openedx.org

Mailing List and IRC Channel
****************************

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/g/edx-code

.. |build-status| image:: https://github.com/openedx/edx-notes-api/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/openedx/edx-notes-api/actions/workflows/ci.yml
