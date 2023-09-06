#!/bin/sh
#Set loop variable to zero
i=0
#Set the output directory
#Pull in first argument as the number of loops
loops=$1
#Pull in the second argument as the output file name
mcs_dir=$2
config_number=$3
interval=$4
#use awk to do some floating point math
uinterval=$(awk 'BEGIN{print $interval*1000000}')
postfix=_mcs
under=_

exit_message="Expecting an # of loops as 1st argument and output directory as second argument, and config number as 3rd. Exit" 

#Check that the number of loops exists, exit if not
if [ -z $loops ]; then
	echo $exit_message
	exit 1
fi

#check that the mcs directory exists
if [ -z $mcs_dir ]; then
	echo $exit_message
	exit 1
fi

#Check that the output file name exists
if [ -z $config_number ]; then
	echo $exit_message
	exit 1
fi

#get the current time
curr_time=`awk 'NR==3{printf int($3/1000000)}' /proc/timer_list`
#find the end time based on the loops in ms
end_time=`echo | awk -v loops=$loops -v curr_time=$curr_time '{printf  curr_time+=loops*1000}'`
#Loop the total number of loops
while [ $curr_time -le $end_time ]; do
	#Pull in the date/time
	date=$(date)
	#Pull in the clock time
	clock=`awk 'NR==3{printf "%.3f", $3/1e+9}' /proc/timer_list`
	#Pull in the mcs list, parsing using external awk script
	#athstats > $mcs_dir/$config_number$under$i$postfix.txt
	mcs_value=`athstats|egrep "MCS|mcs" |awk -f /data/concatenate_tx.awk`
	#If its the first write then start a new file.
	if [ $i == 0 ]; then 
		printf '%s\n' "date,clock,mcs0,mcs1,mcs2,mcs3,mcs4,mcs5,mcs6,mcs7,mcs8,mcs9" |tee $mcs_dir/$config_number$postfix.csv
		printf '%s\n' "\"$date\",$clock,$mcs_value" | tee -a $mcs_dir/$config_number$postfix.csv
	#If its not the first write then append to the file
	else
		printf '%s\n' "\"$date\",$clock,$mcs_value" | tee -a $mcs_dir/$config_number$postfix.csv
	fi
	i=$((i+1))
	#Loop rate
	usleep $uinterval
  curr_time=`awk 'NR==3{printf int($3/1000000)}' /proc/timer_list`
done

#change the output to json using some awk
lines=`cat $mcs_dir/$config_number$postfix.csv|wc -l`
awk -f /data/csv_to_json.awk $mcs_dir/$config_number$postfix.csv -v lines=$lines > $mcs_dir/$config_number$postfix.json
#remove the csv file
rm -f $mcs_dir/$config_number$postfix.csv
