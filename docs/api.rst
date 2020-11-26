API References
==============



ZKClient
--------

.. autoclass:: aiozk.ZKClient

    .. automethod:: start
    .. automethod:: close

    .. automethod:: exists
    .. automethod:: create
    .. automethod:: ensure_path
    .. automethod:: delete
    .. automethod:: deleteall
    .. automethod:: get
    .. automethod:: get_data
    .. automethod:: set
    .. automethod:: set_data
    .. automethod:: get_children
    .. automethod:: get_acl
    .. automethod:: set_acl

    .. automethod:: begin_transaction

Transaction
-----------

.. autoclass:: aiozk.transaction.Transaction
    :members:

.. autoclass:: aiozk.transaction.Result



ACL
---

.. autoclass:: aiozk.ACL

    .. automethod:: make

Stat
----

.. autoclass:: aiozk.protocol.stat.Stat


RetryPolicy
-----------

.. autoclass:: aiozk.RetryPolicy

    .. automethod:: once
    .. automethod:: n_times
    .. automethod:: forever
    .. automethod:: exponential_backoff
    .. automethod:: until_elapsed



Exceptions
----------

.. automodule:: aiozk.exc
    :members:
