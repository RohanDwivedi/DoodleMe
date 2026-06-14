std_msgs/Header header
string session_id
string role            # "assistant" | "tool_call" | "tool_result"
string content
string tool_name       # populated when role == "tool_call" or "tool_result"
bool is_final          # true on the last chunk of an assistant turn
