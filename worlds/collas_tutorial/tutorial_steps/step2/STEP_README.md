# Step 2 - Streams

Same skeleton as step 1, plus: the teacher now creates its **streams** in `accept_new_role` (the method every
agent runs when the world assigns it a role).

- Three lecture groups (`lecture1..3`), each with an **image stream** and a **class-name stream** built from the
  files in `data/lectures/*` (the class is parsed from the file name, e.g. `012_Empoleon.jpg` -> `Empoleon`).
- An `exam` group and a `feedback` group, built the same way from `data/exam` and `data/feedback`.
- `update_streams_in_profile()` publishes the streams in the teacher's profile, so connecting agents can see them.

The streams are not used yet - this step is about discussing the `Stream` objects: groups, image/text streams,
the `delta` pacing (seconds between consecutive samples), private direct-message streams (`pubsub=False`).

**Run it**: same visible behavior as step 1, but the teacher now owns streams (they appear in its profile).
