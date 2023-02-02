#!/usr/bin/env python3

## Helpful to list stacks that are deployed in AWS for the current account and region, 
## see their status and retrieve their outputs without having to go to the 
## AWS Managament Console.
## Tim Wornell

import boto3

def pull_stacks():
    client = boto3.client('cloudformation')
    alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    try:
        stacks = client.describe_stacks()
        region = stacks['Stacks'][0]['StackId'][23:32]
        account = stacks['Stacks'][0]['StackId'][33:45]
        return stacks, region, account, alias
    except Exception as error:
        print(f'{error}\n')
        exit()

def print_output():
    #print(stacks)
    ## create labels and set to display as green text
    label = ['  status:  ', '    created:  ', 'Stack Name: ', 'Description: ', 'Updated: ', ' at: ',
            'Outputs']
    for i in range(len(label)):
        label[i] = f'\x1b[0;32;40m{label[i]}\x1b[0m'

    print()
    print('\x1b[0;30;42m') #black on green!
    print(' *************************************************')
    print('               DEPLOYED STACKS                 ')
    print(f'              Region: {region}                ')      
    print(f'            AccountID: {account}            ')
    print(f'            Account: {alias}            ')
    print(' ************************************************** \x1b[0m')
    print()

    ## print list of stacks
    for i in range(len(stacks['Stacks'])):
        print(f' {i}: '+stacks['Stacks'][i]['StackName']
                +label[0]+stacks['Stacks'][i]['StackStatus']
                +label[1]+stacks['Stacks'][i]['CreationTime'].strftime('%d/%m/%Y'))

    ## take stack number as input and display select information
    while True:
        print()
        try:
            choice = input('Enter a number for details or q to quit: ')
            if choice == 'q':
                exit()
        except:
            choice = 'q'
            exit()
        try:
            item = int(choice)
        except:
            pass
        print()
        try:
            print(label[2]+stacks['Stacks'][item]['StackName'])
            try:
                print(label[3]+stacks['Stacks'][item]['Description'])
            except:
                pass
            try:
                print(label[4]+stacks['Stacks'][item]['LastUpdatedTime'].strftime('%d/%m/%Y')
                +label[5]+stacks['Stacks'][item]['LastUpdatedTime'].strftime('%H:%M:%S'))
            except:
                pass
            try:
                print(label[6])
                for i in range(len(stacks['Stacks'][item]['Outputs'])):
                    print(' '+stacks['Stacks'][item]['Outputs'][i]['OutputKey']
                    +':     '+stacks['Stacks'][item]['Outputs'][i]['OutputValue'])
            except:
                print(' None')
                pass
            print()
        except:
            print('Try again')
            pass

if __name__ == '__main__':
    
    stacks, region, account, alias = pull_stacks()
    #alias = boto3.client('iam').list_account_aliases()['AccountAliases'][0]
    print_output()