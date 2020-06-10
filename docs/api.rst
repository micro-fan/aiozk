API References
==============



ZKClient
--------
.. class:: aiozk.ZKClient(servers, chroot=None, session_timeout=10, default_acl=None, retry_policy=None, allow_read_only=False, read_timeout=None, loop=None)

    The class of Zookeeper Client


    :param str servers: Server list to which ZKClient tries connecting. Specify
                        a comma (``,``) separated server list. A server is
                        defined as ``address``:``port`` format.


    :param str chroot: Root znode path inside Zookeeper data hierarchy.

    :param float session_timeout: Zookeeper session timeout.

    :param default_acl: Default ACL for .create and .ensure_path coroutines. If
                        acl parameter of them is not passed this ACL is used
                        instead. If None is passed for default_acl, then ACL
                        for unrestricted access is applied. This means that
                        scheme is ``world``, id is ``anyone`` and all
                        ``READ``/``WRITE``/``CREATE``/``DELETE``/``ADMIN``
                        permission bits will be set to the new znode.

    :type default_acl: aiozk.protocol.acl.ACL

    :param retry_policy: Retry policy. If None, ``RetryPolicy.forever()`` is
                         used instead.
    :type retry_policy: aiozk.retry.RetryPolicy

    :param bool allow_read_only: True if you allow this client to make use of
                                 read only Zookeeper session, otherwise False.

    :param float read_timeout: Timeout on reading from Zookeeper server in
                               seconds.

    :param loop: event loop. If None, asyncio.get_event_loop() is used.


    .. comethod:: start()

       Start Zookeeper session and await for session connected.

    .. comethod:: close()

       Close Zookeeper session and await for session closed.

    .. comethod:: exists(path, watch=False)

       :param str path: Path of znode

       :param bool watch: If True, a watch is set as a side effect

       :return: True if it exists otherwise False
       :rtype: bool

       Check whether the path exists.

    .. comethod:: create(path, data=None, acl=None, ephemeral=False, sequential=False, container=False)

       :param str path: Path of znode

       :param data: Data which will be stored at the znode if the
                                request succeeds
       :type data: str, bytes

       :param aiozk.protocol.ACL.acl acl: ACL to be set to the new znode.

       :param bool ephemeral: True for creating ephemeral znode otherwise False

       :param bool sequential: True for creating seqeuence znode otherwise
                               False

       :param bool container: True for creating container znode otherwise False

       :return: Path of the created znode
       :rtype: str

       :raises aiozk.exc.NodeExists: Can be raised if a znode at the same path
                                     already exists.

       Create a znode at the path.

    .. comethod:: ensure_path(path, acl=None)

       :param str path: Path of znode

       :param aiozk.protocol.ACL.acl acl: ACL to be set to the new znodes

       Ensure all znodes exist in the path. Missing Znodes will be created.


    .. comethod:: delete(path, force=False)

       :param str path: Path of znode

       :param bool force: True for ignoring version of the znode. A version of
                          a znode is used as an optimistic lock mechanism.
                          Set false for making use of a version that is tracked by
                          a stat cache of ZKClient.

       :raises aiozk.exc.NoNode: Raised if path does not exist.

       Delete a znode at the path.

    .. comethod:: deleteall(path)

       :param str path: Path of znode

       :raises aiozk.exc.NoNode: Raised if path does not exist.

       Delete all znodes in the path recursively.

    .. comethod:: get(path, watch=False)

       :param str path: Path of znode

       :param bool watch: True for setting a watch event as a side effect,
                          otherwise False

       :return: Data and stat of znode
       :rtype: (bytes, aiozk.protocol.stat.Stat)

       :raises aiozk.exc.NoNode: Can be raised if path does not exist

       Get data as bytes and stat of znode.

    .. comethod:: get_data(path, watch=False)

       :param str path: Path of znode

       :param bool watch: True for setting a watch event as a side effect,
                          otherwise False

       :return: Data
       :rtype: bytes

       :raises aiozk.exc.NoNode: Can be raised if path does not exist

       Get data as bytes.

    .. comethod:: set(path, data, version)

       :param str path: Path of znode

       :param data: Data to store at znode
       :type data: str or bytes

       :param int version: Version of znode data to be modified.

       :return: Response stat
       :rtype: aiozk.protocol.stat.Stat

       :raises aiozk.exc.NoNode: Raised if znode does not exist

       :raises aiozk.exc.BadVersion: Raised if version does not match the
                                     actual version of the data. The update
                                     failed.

       Set data to znode. Prefer using .set_data than this method unless you
       have to control the concurrency.

    .. comethod:: set_data(path, data, force=False)

       :param str path: Path of znode

       :param data: Data to be stored at znode
       :type data: bytes or str

       :param bool force: True for ignoring data version. False for using
                          version from stat cache.

       :raises aiozk.exc.NoNode: Raised if znode does not exist

       :raises aiozk.exc.BadVersion: Raised if force parameter is False and
                                     only if supplied version from stat cache
                                     does not match the actual version of znode
                                     data.

       Set data to znode without needing to handle version.

    .. comethod:: get_children(path, watch=False)

       :param str path: Path of znode

       :param bool watch: True for setting a watch event as a side effect
                          otherwise False

       :return: Names of children znodes
       :rtype: [str]

       :raises aiozk.exc.NoNode: Raised if znode does not exist

       Get all children names. Returned names are only basename and they does
       not include dirname.

    .. comethod:: get_acl(path)

       :param str path: Path of znode

       :return: List of ACLs associated with the znode
       :rtype: [aiozk.protocol.acl.ACL]

       Get list of ACLs associated with the znode

    .. comethod:: set_acl(path, acl, force=False)

       :param str path: Path of znode

       :param acl: ACL for the znode
       :type acl: aiozk.protocol.acl.ACL

       :param bool force: True for ignoring ACL version of the znode when
                          setting ACL to the actual znode. False for using ACL
                          version from the stat cache.

       :raises aiozk.exc.NoNode: Raised if znode does not exist

       :raises aiozk.exc.BadVersion: Raised if force parameter is False and
                                     only if the supplied version from stat
                                     cache does not match the actual ACL
                                     version of the znode.

       Set ACL to the znode.

    .. method:: begin_transaction()

       :return: Transaction instance which can be used for adding read/write
                operations
       :rtype: aiozk.transaction.Transaction

       Return Transaction instance which provides methods for read/write
       operations and commit method. This instance is used for transaction
       request.


Transaction
-----------

Todo


ACL
---

Todo


Stat
----

Todo


RetryPolicy
-----------

Todo


Exceptions
----------

Todo
