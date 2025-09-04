#!/bin/bash

files=("log/run_w.py.log" "log/run_1.py.log" "log/run_2.py.log" "log/run_3.py.log" "log/run_4.py.log")
agents=("WORLD" "TEACH" "STUD1" "STUD2" "STUD3")

# Generate summary and store in a variable
public_keys=()
public_repl=()
private_keys=()
private_repl=()
summary=""
for i in "${!files[@]}"; do
    file="${files[$i]}"
    agent="${agents[$i]}"

    # Extract the exact keys
    public=$(grep -o "public: [^,)]*" "$file" | tail -n1 | awk '{print $2}')
    private=$(grep -o "private: [^,)]*" "$file" | tail -n1 | awk '{print $2}')

    # Store keys and their replacement labels
    public_keys+=("$public")
    public_repl+=("~${agent}_PUBL~")
    private_keys+=("$private")
    private_repl+=("~${agent}_PRIV~")

    public=$(grep -o "public: [^,)]*" "$file" | tail -n1 | awk '{print substr($2,length($2)-2,3)}')
    private=$(grep -o "private: [^,)]*" "$file" | tail -n1 | awk '{print substr($2,length($2)-2,3)}')
    summary+="$agent\tpublic: ...$public\tprivate: ...$private\n"
done

# Loop through files and process with awk
for file in "${files[@]}"; do
    # Generate output filename
    out_file="${file/.log/.dump.log}"
    echo -e "Dumping to ${out_file}..."

    awk -v y="Connect|Disconnect|disconnect|Removing|Current status of the pools|Not enqueued" -v summary="$summary" -v agent="$agent" '
    {
      lines[NR] = $0

      if (match($0, /cycle: [0-9]+\]/)) {
        num = substr($0, RSTART+7, RLENGTH-8)
        if (!(num in first_cycle)) first_cycle[num] = NR
        last_cycle[num] = NR
      }

      if ($0 ~ y) yline[NR] = 1
    }
    END {
      block_id = 0
      for (ln = 1; ln <= NR; ln++) {
        for (n in first_cycle) {
          if (first_cycle[n] == ln) {
            start = first_cycle[n]
            stop  = last_cycle[n]

            has_y = 0
            for (i = start; i <= stop; i++) if (i in yline) { has_y = 1; break }

            if (has_y) {
              block_id++
              print "*************************************************************"
              print "                 BLOCK " block_id " (cycle=" n ")"
              print "*************************************************************"

              # Print summary with agent prefix
              split(summary, sum_lines, "\n")
              for (s in sum_lines) if (sum_lines[s] != "") print sum_lines[s]

              print "*************************************************************"

              # Print block lines with agent prefix
              for (i = start; i <= stop; i++) print agent "\t" lines[i]
              print ""
            }
          }
        }
      }
    }
    ' "$file" | grep -Ev "\[DEBUG HSM\] Requested action found|\[DEBUG HSM\] Comparing with action|\[DEBUG HSM\] Tried and failed|\[DEBUG HSM\] Policy selected|\[DEBUG HSM\] Returned|\[DEBUG HSM\] Multi-step action|\[DEBUG HSM\] checking if|\[DEBUG HSM\] Cannot-be-run-anymore" | while IFS= read -r line; do
          # Replace exact public/private keys on the fly
          for j in "${!public_keys[@]}"; do
              line=${line//${public_keys[j]}/${public_repl[j]}}
          done
          for j in "${!private_keys[@]}"; do
              line=${line//${private_keys[j]}/${private_repl[j]}}
          done
          echo "$line"
      done > "$out_file"
done
