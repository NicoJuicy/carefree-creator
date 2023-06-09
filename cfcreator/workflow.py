import time

import numpy as np

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from fastapi import Response
from pydantic import Field
from cftool.data_structures import WorkNode
from cftool.data_structures import Workflow

from .common import get_response
from .common import IAlgorithm
from .common import ReturnArraysModel


workflow_endpoint = "/workflow"


class WorkflowModel(ReturnArraysModel):
    nodes: List[WorkNode] = Field(..., description="The nodes in the workflow.")
    target: str = Field(..., description="The target node.")
    caches: Optional[Dict[str, Any]] = Field(None, description="The preset caches.")


@IAlgorithm.auto_register()
class WorkflowAlgorithm(IAlgorithm):
    model_class = WorkflowModel

    algorithms: Optional[Dict[str, IAlgorithm]] = None
    last_workflow: Optional[Workflow] = None

    endpoint = workflow_endpoint

    def initialize(self) -> None:
        from cfcreator.sdks.apis import APIs
        from cfcreator.sdks.apis import ALL_LATENCIES_KEY

        if self.algorithms is None:
            raise ValueError("`algorithms` should be provided for `WorkflowAlgorithm`.")
        self.apis = APIs(algorithms=self.algorithms)
        self.latencies_key = ALL_LATENCIES_KEY

    async def run(self, data: WorkflowModel, *args: Any, **kwargs: Any) -> Response:
        self.log_endpoint(data)
        t0 = time.time()
        workflow = Workflow()
        for node in data.nodes:
            workflow.push(node)
        self.last_workflow = workflow
        t1 = time.time()
        results = await self.apis.execute(workflow, data.target, data.caches)
        t2 = time.time()
        target_result = results[data.target]
        if isinstance(target_result[0], str):
            raise ValueError("The target node should return images.")
        arrays = list(map(np.array, target_result))
        t3 = time.time()
        res = get_response(data, arrays)
        latencies = {
            "get_workflow": t1 - t0,
            "inference": t2 - t1,
            "postprocess": t3 - t2,
            "get_response": time.time() - t3,
        }
        self.log_times(latencies)
        self.last_latencies["inference_details"] = results[self.latencies_key]
        return res


__all__ = [
    "workflow_endpoint",
    "WorkflowModel",
    "WorkflowAlgorithm",
]
