"""File Catalog MongoDB Interface."""


from __future__ import absolute_import, division, print_function

import asyncio
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Generator, List, Optional, Union, cast

import pymongo  # type: ignore[import]
from motor.motor_tornado import MotorClient  # type: ignore[import]
from motor.motor_tornado import MotorCursor

from .schema import types

logger = logging.getLogger("mongo")


class AllKeys:  # pylint: disable=R0903
    """Include all keys in MongoDB find*() methods."""


class Mongo:
    """A ThreadPoolExecutor-based MongoDB client."""

    def __init__(  # pylint: disable=R0913
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        authSource: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        uri: Optional[str] = None,
    ) -> None:

        if uri:
            logger.info(f"MongoClient args: uri={uri}")
            self.client = MotorClient(uri, authSource=authSource).file_catalog
        else:
            logger.info(
                "MongoClient args: host=%s, port=%s, username=%s", host, port, username
            )
            self.client = MotorClient(
                host=host,
                port=port,
                authSource=authSource,
                username=username,
                password=password,
            ).file_catalog

        asyncio.get_event_loop().run_until_complete(self.create_indexes())
        self.executor = ThreadPoolExecutor(max_workers=10)
        logger.info("done setting up Mongo")

    async def create_indexes(self) -> None:
        """Create indexes for all file-catalog mongo collections."""
        # all files (a.k.a. required fields)
        await self.client.files.create_index("uuid", unique=True, background=True)
        await self.client.files.create_index(
            "logical_name", unique=True, background=True
        )
        await self.client.files.create_index(
            [("logical_name", pymongo.HASHED)], background=True
        )
        await self.client.files.create_index("locations", unique=True, background=True)
        await self.client.files.create_index(
            [
                ("locations.site", pymongo.DESCENDING),
                ("locations.path", pymongo.DESCENDING),
            ],
            background=True,
        )
        await self.client.files.create_index("locations.archive", background=True)
        await self.client.files.create_index("create_date", background=True)

        # all .i3 files
        await self.client.files.create_index(
            "content_status", sparse=True, background=True
        )
        await self.client.files.create_index(
            "processing_level", sparse=True, background=True
        )
        await self.client.files.create_index("data_type", sparse=True, background=True)

        # data_type=real files
        await self.client.files.create_index("run_number", sparse=True, background=True)
        await self.client.files.create_index(
            "start_datetime", sparse=True, background=True
        )
        await self.client.files.create_index(
            "end_datetime", sparse=True, background=True
        )
        await self.client.files.create_index(
            "offline_processing_metadata.first_event", sparse=True, background=True
        )
        await self.client.files.create_index(
            "offline_processing_metadata.last_event", sparse=True, background=True
        )
        await self.client.files.create_index(
            "offline_processing_metadata.season", sparse=True, background=True
        )

        # data_type=simulation files
        await self.client.files.create_index(
            "iceprod.dataset", sparse=True, background=True
        )

        # # Collections
        await self.client.collections.create_index("uuid", unique=True, background=True)
        await self.client.collections.create_index("collection_name", background=True)
        await self.client.collections.create_index("owner", background=True)

        # # Snapshots
        await self.client.snapshots.create_index("uuid", unique=True, background=True)
        await self.client.snapshots.create_index("collection_id", background=True)
        await self.client.snapshots.create_index("owner", background=True)

    @staticmethod
    def _get_projection(
        keys: Optional[Union[List[str], AllKeys]] = None,
        default: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, bool]:
        projection = {"_id": False}

        if not keys:
            if default:  # use default keys if they're available
                projection.update(default)
        elif isinstance(keys, AllKeys):
            pass  # only use "_id" constraint in projection
        elif isinstance(keys, list):
            projection.update({k: True for k in keys})
        else:
            raise TypeError(
                f"`keys` argument ({keys}) is not NoneType, list, or AllKeys"
            )

        return projection

    @staticmethod
    def _limit_results(
        cursor: MotorCursor, limit: Optional[int] = None, start: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        """Get sublist of results from `cursor` using `limit` and `start`.

         `limit` and `skip` are ignored by __getitem__:
         http://api.mongodb.com/python/current/api/pymongo/cursor.html#pymongo.cursor.Cursor.__getitem__

        Therefore, implement it manually.
        """
        end = None
        if limit is not None:
            end = start + limit

        i = 0
        async for row in cursor:
            if i < start:
                continue
            yield row
            if end and i >= end:
                return
            i += 1

    async def find_files(
        self,
        query: Optional[Dict[str, Any]] = None,
        keys: Optional[Union[List[str], AllKeys]] = None,
        limit: Optional[int] = None,
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find files.

        Optionally, apply keyword arguments. "_id" is always excluded.

        Decorators:
            run_on_executor

        Keyword Arguments:
            query -- MongoDB query
            keys -- fields to include in MongoDB projection
            limit -- max count of files returned
            start -- starting index

        Returns:
            List of MongoDB files
        """
        projection = Mongo._get_projection(
            keys, default={"uuid": True, "logical_name": True}
        )
        cursor = await self.client.files.find(query, projection)
        results = list(Mongo._limit_results(cursor, limit, start))

        return results

    async def count_files(  # pylint: disable=W0613
        self, query: Optional[Dict[str, Any]] = None, **kwargs: Any,
    ) -> int:
        """Get count of files matching query."""
        if not query:
            query = {}

        ret = await self.client.files.count_documents(query)

        return cast(int, ret)

    async def create_file(self, metadata: types.Metadata) -> str:
        """Insert file metadata.

        Return uuid.
        """
        result = await self.client.files.insert_one(metadata)

        if (not result) or (not result.inserted_id):
            msg = "did not insert new file"
            logger.warning(msg)
            raise Exception(msg)

        return metadata["uuid"]

    async def get_file(self, filters: Dict[str, Any]) -> types.Metadata:
        """Get file matching filters."""
        file = await self.client.files.find_one(filters, {"_id": False})
        return cast(types.Metadata, file)

    async def update_file(self, uuid: str, metadata: types.Metadata) -> None:
        """Update file."""
        result = await self.client.files.update_one({"uuid": uuid}, {"$set": metadata})

        if result.modified_count is None:
            logger.warning(
                "Cannot determine if document has been modified since `result.modified_count` has the value `None`. `result.matched_count` is %s",
                result.matched_count,
            )
        elif result.modified_count != 1:
            msg = f"updated {result.modified_count} files with id {uuid}"
            logger.warning(msg)
            raise Exception(msg)

    async def replace_file(self, metadata: types.Metadata) -> None:
        """Replace file.

        Metadata must include 'uuid'.
        """
        uuid = metadata["uuid"]

        result = await self.client.files.replace_one({"uuid": uuid}, metadata)

        if result.modified_count is None:
            logger.warning(
                "Cannot determine if document has been modified since `result.modified_count` has the value `None`. `result.matched_count` is %s",
                result.matched_count,
            )
        elif result.modified_count != 1:
            msg = f"updated {result.modified_count} files with id {uuid}"
            logger.warning(msg)
            raise Exception(msg)

    async def delete_file(self, filters: Dict[str, Any]) -> None:
        """Delete file matching filters."""
        result = await self.client.files.delete_one(filters)

        if result.deleted_count != 1:
            msg = f"deleted {result.deleted_count} files with filter {filters}"
            logger.warning(msg)
            raise Exception(msg)

    async def find_collections(
        self,
        keys: Optional[Union[List[str], AllKeys]] = None,
        limit: Optional[int] = None,
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find all collections.

        Optionally, apply keyword arguments. "_id" is always excluded.

        Keyword Arguments:
            keys -- fields to include in MongoDB projection
            limit -- max count of collections returned
            start -- starting index

        Returns:
            List of MongoDB collections
        """
        projection = Mongo._get_projection(keys)  # show all fields by default
        cursor = await self.client.collections.find({}, projection)
        results = list(Mongo._limit_results(cursor, limit, start))

        return results

    async def create_collection(self, metadata: Dict[str, Any]) -> str:
        """Create collection, insert metadata.

        Return uuid.
        """
        result = await self.client.collections.insert_one(metadata)

        if (not result) or (not result.inserted_id):
            msg = "did not insert new collection"
            logger.warning(msg)
            raise Exception(msg)

        return cast(str, metadata["uuid"])

    async def get_collection(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get collection matching filters."""
        collection = await self.client.collections.find_one(filters, {"_id": False})
        return cast(Dict[str, Any], collection)

    async def find_snapshots(
        self,
        query: Optional[Dict[str, Any]] = None,
        keys: Optional[Union[List[str], AllKeys]] = None,
        limit: Optional[int] = None,
        start: int = 0,
    ) -> List[Dict[str, Any]]:
        """Find snapshots.

        Optionally, apply keyword arguments. "_id" is always excluded.

        Keyword Arguments:
            query -- MongoDB query
            keys -- fields to include in MongoDB projection
            limit -- max count of snapshots returned
            start -- starting index

        Returns:
            List of MongoDB snapshots
        """
        projection = Mongo._get_projection(keys)  # show all fields by default
        cursor = await self.client.snapshots.find(query, projection)
        results = list(Mongo._limit_results(cursor, limit, start))

        return results

    async def create_snapshot(self, metadata: Dict[str, Any]) -> str:
        """Insert metadata into 'snapshots' collection.

        Return uuid.
        """
        result = await self.client.snapshots.insert_one(metadata)

        if (not result) or (not result.inserted_id):
            msg = "did not insert new snapshot"
            logger.warning(msg)
            raise Exception(msg)

        return cast(str, metadata["uuid"])

    async def get_snapshot(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Find snapshot, optionally filtered."""
        snapshot = await self.client.snapshots.find_one(filters, {"_id": False})
        return cast(Dict[str, Any], snapshot)

    async def append_distinct_elements_to_file(
        self, uuid: str, metadata: Dict[str, Any]
    ) -> None:
        """Append distinct elements to arrays within a file document."""
        # build the query to update the file document
        update_query: Dict[str, Any] = {"$addToSet": {}}
        for key in metadata:
            if isinstance(metadata[key], list):
                update_query["$addToSet"][key] = {"$each": metadata[key]}
            else:
                update_query["$addToSet"][key] = metadata[key]

        # update the file document
        update_query["$set"] = {"meta_modify_date": str(datetime.datetime.utcnow())}
        result = await self.client.files.update_one({"uuid": uuid}, update_query)

        # log and/or throw if the update results are surprising
        if result.modified_count is None:
            logger.warning(
                "Cannot determine if document has been modified since `result.modified_count` has the value `None`. `result.matched_count` is %s",
                result.matched_count,
            )
        elif result.modified_count != 1:
            msg = f"updated {result.modified_count} files with id {uuid}"
            logger.warning(msg)
            raise Exception(msg)
