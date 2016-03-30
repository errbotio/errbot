Flows Concepts
==============

Static structure
----------------

Flows are represented as graphs. Those graphs have a root (FlowRoot) which is basically their entry point and
are composed of nodes (FlowNodes). Every node represents an Errbot command.
Connecting those nodes, you have predicates, we will see their function below.

Execution
---------

At execution time, Errbot will keep track of who started the flow and at what step (node) it is currently.
On top of that Errbot will initialize a context for the entire conversation. The context is a simple python dictionary
and it is attached to only one conversation. Think of this like the persistence for plugins but linked to
a conversation only.

If you don't specify any predicate when you build your flow, every single step is "manual". It means that Errbot will
 wait for the user to execute one of the possible command at every step to advance along the graph.

Predicates can be use to trigger automatically a command. Predicates are simple functions saying to Errbot,
"this command has enough in the context to be able to executed without any user intervention".
At any time if a predicate is verified after a step is executed, Errbot will proceed and execute the next step.
