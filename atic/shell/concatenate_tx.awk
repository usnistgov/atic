#Expecting input from the athstats executable in the format of:
#
# Tx MCS STATS:
# mcs 0- mcs 4 STATS:     0,12748065,125946566,185016009,358433286,
# mcs 5- mcs 9 STATS:286991137,127597531,340592172,6524414,     0,


#find the Tx mcs line
{if($1=="Tx"){
			#grab the first line
			getline;
			#get rid of junk 
	      	split($0,a,":");
			#split the mcs values of first line into b
			split(a[2],b,",");
			#grab the second line
			getline;
			#get rid of junk
			split($0,a,":");
			#split the mcs values of the second line into c
			split(a[2],c,",")
			#output as a single csv line
			print b[1]","b[2]","b[3]","b[4]","b[5]","c[1]","c[2]","c[3]","c[4]","c[5];
			}
}
