"""Tool registry — maps Claude tool names to Python callables and JSON schemas."""

from __future__ import annotations

from .openscad_tool import write_openscad, render_stl
from .urdf_tool import write_urdf
from .bom_tool import update_bom
from .wiring_tool import generate_wiring
from .kicad_tool import export_kicad

TOOL_REGISTRY = {
    "write_openscad": write_openscad,
    "render_stl": render_stl,
    "write_urdf": write_urdf,
    "update_bom": update_bom,
    "generate_wiring": generate_wiring,
    "export_kicad": export_kicad,
}

TOOL_SCHEMAS = [
    {
        "name": "write_openscad",
        "description": (
            "Write or overwrite the parametric OpenSCAD model file. "
            "Always call render_stl after this to update the 3D preview."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Complete OpenSCAD source code",
                },
                "filename": {
                    "type": "string",
                    "description": "Filename within the workspace, e.g. 'model.scad'",
                    "default": "model.scad",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "render_stl",
        "description": (
            "Render a .scad file to STL using OpenSCAD. "
            "The UI will automatically display the resulting mesh."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scad_filename": {
                    "type": "string",
                    "description": "Filename of the .scad source to render",
                    "default": "model.scad",
                },
                "stl_filename": {
                    "type": "string",
                    "description": "Output STL filename",
                    "default": "model.stl",
                },
            },
            "required": [],
        },
    },
    {
        "name": "write_urdf",
        "description": (
            "Write or update the robot URDF description file. "
            "Dimensions must be in metres. "
            "Automatically published to /robot_description if auto-publish is enabled."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Complete URDF XML content",
                },
                "filename": {
                    "type": "string",
                    "description": "URDF filename within the workspace",
                    "default": "robot.urdf",
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "update_bom",
        "description": "Add, update, or remove components in the Bill of Materials.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "remove", "clear"],
                    "description": "Operation to perform on the BOM",
                },
                "item": {
                    "type": "object",
                    "description": "Component details (for add/update)",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "electronics", "mechanical", "fastener",
                                "cable", "sensor", "actuator", "power", "other"
                            ],
                        },
                        "qty": {"type": "integer", "minimum": 1},
                        "supplier": {"type": "string"},
                        "part_number": {"type": "string"},
                        "unit_price": {"type": "number"},
                        "notes": {"type": "string"},
                    },
                    "required": ["id", "name"],
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "generate_wiring",
        "description": (
            "Write a Mermaid wiring diagram showing how all electronic components connect. "
            "Use 'graph LR' layout. Label edges with signal types (PWM, I2C, SPI, 5V, GND, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "diagram": {
                    "type": "string",
                    "description": "Complete Mermaid diagram source",
                },
            },
            "required": ["diagram"],
        },
    },
    {
        "name": "export_kicad",
        "description": "Generate a KiCad schematic file (.kicad_sch) for the electronics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Schematic title",
                    "default": "DoodleMe Robot",
                },
                "components": {
                    "type": "array",
                    "description": "List of schematic symbols",
                    "items": {
                        "type": "object",
                        "properties": {
                            "ref": {"type": "string", "description": "Reference designator, e.g. U1"},
                            "value": {"type": "string", "description": "Component value, e.g. Arduino Nano"},
                            "footprint": {"type": "string"},
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                        },
                        "required": ["ref", "value"],
                    },
                },
                "nets": {
                    "type": "array",
                    "description": "List of net connections",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "pins": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "ref": {"type": "string"},
                                        "pin": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "required": ["components"],
        },
    },
]
