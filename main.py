remote=0

    #process every source wiki entry in config json array
    jq -c '.[]' $(Agent.BuildDirectory)/self/config.json | while read i; do

      #create a folder for every source wiki
      cd $(Agent.BuildDirectory)
      ((remote=remote+1))
      mkdir "$remote"

      cd $(Agent.BuildDirectory)/$remote
      echo "clone $(echo "$i" | jq -r '.sourceWiki')"
      repo=$(echo "$i" | jq -r '.sourceWiki') 
      repo="${repo:0:8}Pipeline:$(System.AccessToken)${repo:12}"
      git clone $repo $(Agent.BuildDirectory)/$remote || exit 1
      git checkout $(echo "$i" | jq -r '.sourceWikiBranch') 


      for k in $(jq '.sources | keys | .[]' <<< "$i"); do

      sourcePath=$(echo "$i" | jq -r --arg jqk  "$k" '.sources[$jqk |tonumber].sourcePath') 
      targetPath=$(echo "$i" | jq -r --arg jqk  "$k" '.sources[$jqk |tonumber].targetPath')

      #copying to target
      if [ "${#sourcePath}" -gt 0 ]; then

        cd $(Agent.BuildDirectory)/$remote
        echo "Checkout $(echo "$i" | jq -r '.sourceWikiBranch')"
        git checkout $(echo "$i" | jq -r '.sourceWikiBranch') 


        source="**<font color="#FF0000">Source Path invalid Please check source and config json!</font>**"
        sourcehash=invalid
        source="$(echo "$i" | jq -r '.sourceWiki')?path=$sourcePath"
        sourcehash=$(git log -n 1 --pretty=format:'%H'  -- "$(Agent.BuildDirectory)/$remote/$sourcePath")
        creator=$(git log -n 1 --pretty=format:'%an'  -- "$(Agent.BuildDirectory)/$remote/$sourcePath")

        RsyncContent=true

        #start scanning the extending header
        if [[ -f "$(Agent.BuildDirectory)/$remote/$sourcePath" ]]; then
          while read line
          do 
            #check if source hash is alrady synchronized
            if [[ "$line" == *"Source Hash"* ]]; then    

                if [[ "$line" == *"$sourcehash"* ]]; then   

                  echo "$(Agent.BuildDirectory)/target/$targetPath" is up to date
                  RsyncContent=false
               fi
              fi
          
              #header has ended
              if [[ "$line" == *"document header end"* ]]; then
                break
              fi
          done < $(Agent.BuildDirectory)/target/$targetPath
        fi

        #rsync content if target is empty or source hash has changed 
        if $RsyncContent ; then

          #git checkout target
          cd $(Agent.BuildDirectory)/target
          echo "Checkout $(targetBranchName)"
          git checkout $(targetBranchName)

          # rsync the current content
          if [[ -f "$(Agent.BuildDirectory)/$remote/$sourcePath" ]]; then

          echo "$(Agent.BuildDirectory)/target/$targetPath" resync
          rsync -av --progress $(Agent.BuildDirectory)/$remote/$sourcePath $(Agent.BuildDirectory)/target/$targetPath --exclude .git
          
            #check if file contains attachments pattern for ![filename.filetype](/.attachments/filename.filetype)
            grep -E "^((!.*\]\(\/)+(.*))$" $(Agent.BuildDirectory)/target/$targetPath | while read -r line ; do
              echo "Processing $line"
              #pattern for .attachments/filename.filetype
              if [[ "$line" =~ (.attachments)\/([a-zA-Z0-9\%\.\/\_\s\-]*) ]] || [[ "$line" =~ (.documents)\/([a-zA-Z0-9\%\.\/\_\s\-]*) ]] ; then
                filename=$(Agent.BuildDirectory)/target/${BASH_REMATCH[0]}
                #get the path of the attachment
                path="${filename%/*}/"
                #create the same path for the target wiki
                mkdir -p "$path"
                #uncode potential URL attachment string
                filenameURL="${BASH_REMATCH[0]}"
                filenameUNURL=$(printf '%b\n' "${filenameURL//%/\\x}")
                #copy attachment to target wiki
                cp "$(Agent.BuildDirectory)/$remote/$filenameUNURL" "$(Agent.BuildDirectory)/target/$filenameUNURL"
                git add "$(Agent.BuildDirectory)/target/$filenameUNURL"
              else
               echo "Invalid file name"
              fi
            done
            filename="$(basename -- $(Agent.BuildDirectory)/target/$targetPath)"
          else
            echo "$(Agent.BuildDirectory)/target/$targetPath" Source Path invalid Please check source and config json!
            >$(Agent.BuildDirectory)/target/$targetPath
            echo "**<font color="#FF0000">Source Path invalid Please check source and config json!</font>**" >> $(Agent.BuildDirectory)/target/$targetPath
          fi


          #add a new document header
          sed -i "1 i\ " $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\ " $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i[![Build Status](https://dev.azure.com/vwac/Customer%20Support%20Helpdesk/_apis/build/status/CSOTopicsStatus?repoName=CSOTopicsStatus&branchName=develop)](https://dev.azure.com/vwac/Customer%20Support%20Helpdesk/_build/latest?definitionId=2959&repoName=CSOTopicsStatus&branchName=develop)" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\ " $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\ " $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\[document header end]: <> (comment to identify documents header end with scripts)" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Release Date**          |   |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Review Date**           |   |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Source Hash**           |  $sourcehash  |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Source**                |  $source |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Reviewer**              |   |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Creator**               | $creator  |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Version**               |   |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i '1 i\| **Status**                | <div style="color:white;background-color:red;padding: 5px;width: 150px;text-align: center;border-radius: 25px;">Draft</div> |' $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| **Name**                  |  $filename |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\|---------------------------|------------------------------------------------------------------------------------------------------------------|" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\| Attribute                 | Value |" $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\ " $(Agent.BuildDirectory)/target/$targetPath
          sed -i "1 i\[document header begin]: <> (comment to identify documents header begin with scripts)" $(Agent.BuildDirectory)/target/$targetPath
        
          # remove reference to UNECE Approved by
          sed  -i -e 's/[^\|]*\|$//14' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath

          # remove reference to PPE Approved by	
          sed  -i -e 's/[^\|]*\|$//13' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath

          # remove reference to Approval UNECE	
          sed  -i -e 's/[^\|]*\|$//12' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath

          # remove reference to Approval PPE		
          sed  -i -e 's/[^\|]*\|$//11' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath

          # remove reference Requester		
          sed  -i -e 's/[^\|]*\|$//10' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath

          # remove reference CR Link			
          sed  -i -e 's/[^\|]*\|$//9' $(Agent.BuildDirectory)/target/$targetPath
          sed  -i 's/||/|/1' $(Agent.BuildDirectory)/target/$targetPath




        git add *
        git commit --message "Auto Docu Update"
        git push
        
        fi
      
      fi
    done
    done
    


  displayName: 'Merge Sources wikis to Target Wiki'
