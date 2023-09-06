BEGIN{
  FS=","
  OFS=""
  getline
  for(i=1;i<=NF;i++)
  names[i] = ($i)
  print "["
}
{
  printf "  %s{"
  for(i=1;i<=NF;i++)
  {
    printf "\"%s\": %s%s",names[i],($i),(i == NF ? "" : ",")
  }
  if(NR==lines)
    print "}"
  else
    print "},"
}
END{
  printf "]"
}
