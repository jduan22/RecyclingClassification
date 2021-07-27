import tensorflow
import keras
import numpy as np
import matplotlib.pyplot as plt
import sys
import feature
import cv2
import os
import random
import constants as C
from time import time
from keras.utils import to_categorical
from keras.models import Sequential
from keras.layers import Dense, Dropout
from keras.layers import Conv2D
from keras.layers import MaxPooling2D
from keras.callbacks import TensorBoard,ModelCheckpoint,CSVLogger
#import batchExtraction

#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################
#given an image and its mask writes the results as fout
def outputResults(image,mask,fout='segmentation.png'):

    #create the segmented image
    canvas = image.copy()
    canvas[mask == -1] = [0,0,0]
    canvas[mask == 0] = [0,0,255]
    canvas[mask == 1] = [0,255,0]
    canvas[mask == 2] = [255,0,0]
    canvas[mask == 3] = [0,255,255]
    canvas[mask == 4] = [255,0,255]
    canvas[mask == 5] = [255,255,0]

    #show the original image and the segmented image and then save the results
    cv2.imwrite(fout,canvas)

    #count the percentage of each category
    cat0_count = np.count_nonzero(mask == -1)
    cat1_count = np.count_nonzero(mask == 0)
    cat2_count = np.count_nonzero(mask == 1)
    cat3_count = np.count_nonzero(mask == 2)
    cat4_count = np.count_nonzero(mask == 3)
    cat5_count = np.count_nonzero(mask == 4)
    cat6_count = np.count_nonzero(mask == 5)
    total = cat1_count + cat2_count + cat3_count + cat4_count + cat5_count + cat6_count + cat0_count

    #get the percentage of each category
    p1 = cat1_count / total
    p2 = cat2_count / total
    p3 = cat3_count / total
    p4 = cat4_count / total
    p5 = cat5_count / total
    p6 = cat6_count / total

    #output to text file
    with open('results.txt','a') as f:
        f.write("\nusing model: %s\n" % sys.argv[3])
        f.write("evaluate image: %s\n\n" % sys.argv[2])
        f.write("--------------------------------------------------------------------------------------\n")
        f.write("%s : %f\n" % (C.CAT1,p1))
        f.write("%s : %f\n" % (C.CAT2,p2))
        f.write("%s : %f\n" % (C.CAT3,p3))
        f.write("%s : %f\n" % (C.CAT4,p4))
        f.write("%s : %f\n" % (C.CAT5,p5))
        f.write("%s : %f\n" % (C.CAT6,p6))
        f.write("--------------------------------------------------------------------------------------\n")
        f.write("------------------------------------END-----------------------------------------------\n")
        f.write("--------------------------------------------------------------------------------------\n")

        greatest = max(cat1_count,cat2_count,cat3_count,cat4_count)

        #f.write out to the terminal what the most common category was for the image
        if(greatest == cat1_count):
            f.write("\nthe most common category is: " + C.CAT1)
        elif(greatest == cat2_count):
            f.write("\nthe most common category is: " + C.CAT2)
        elif(greatest == cat3_count):
            f.write("\nthe most common category is: " + C.CAT3)
        elif(greatest == cat4_count):
            f.write("\nthe most common category is: " + C.CAT4)
        elif(greatest == cat5_count):
            f.write("\nthe most common category is: " + C.CAT5)
        elif(greatest == cat6_count):
            f.write("\nthe most common category is: " + C.CAT6)
        else:
            f.write("\nsorry something went wrong counting the predictions")

#generate predictions on the image using the trained network
def generate_prediction(imgfile, network):

    #extract features from blobs
    print("Getting features...")
    image = cv2.imread(imgfile,cv2.IMREAD_COLOR)
    h,w = image.shape[:2]
    if h > C.FULL_IMGSIZE or w > C.FULL_IMGSIZE:
        image = cv2.resize(image,(C.FULL_IMGSIZE,C.FULL_IMGSIZE),interpolation=cv2.INTER_CUBIC)
    x_test,y_test,markers = feature.extractImage(image,imgfile)

    #get predictions
    print("Getting Predictions...")
    rawpredictions = network.predict_on_batch(x_test)
    predictions = rawpredictions.argmax(axis=1)

    #create mask from predictions
    print("writing results")
    h,w = image.shape[:2]
    best_guess = np.full((h,w),-1)
    for l,p in zip(np.unique(markers),predictions):
        best_guess[markers == l] = p

    #write the results as an image
    if not os.path.isdir('results'):
        os.makedirs('results')
    fileout = 'learnedseg_nn_' + os.path.splitext(os.path.basename(imgfile))[0]  + ".png"
    fileout = os.path.join('results',fileout)
    outputResults(image,np.array(best_guess),fout=fileout)

    #save the raw file
    if not os.path.isdir('raws'):
        os.makedirs('raws')
    filename ='rawoutput_nn_' + os.path.splitext(os.path.basename(imgfile))[0] + '.txt'
    full_dir = os.path.join('raws',filename)
    with open(full_dir,'w') as fout:
        for raw,cat,mark in zip(rawpredictions,predictions,np.unique(markers)):
            fout.write(str("cat: " + str(cat) + '    mark: ' + str(mark) + '    raw: '))
            for val in raw:
                fout.write(str(val) + ',')
            fout.write('\n')

#################################################################################################
#################################################################################################
#################################################################################################

#main method
if __name__ == '__main__':

    if len(sys.argv) == 3 and sys.argv[1] == 'train':
        dataFolder = 'split_' + sys.argv[2].split(".")[0]
        if not os.path.exists('splitData/' + dataFolder):
            print("ERROR: The pca data file name didn't exist")
            sys.exit()
        #define the model
        model = Sequential()
        model.add(Dense(units=100,activation='tanh', input_dim=1223)) # This input_dim needs to be changed based on what data is being fed in
        model.add(Dropout(0.5))
        model.add(Dense(units=100,activation='tanh'))
        model.add(Dropout(0.5))
        model.add(Dense(units=6,activation='tanh'))

        #create or log and model save locations
        if not os.path.isdir('model'):
            os.makedirs('model')
        if not os.path.isdir('log'):
            os.makedirs('log')

        fileCount = len(os.listdir('modelEpochInfo/'))

        #initialize model
        model.compile(loss='binary_crossentropy', optimizer='adadelta', metrics=['accuracy'])
        tensorboard = TensorBoard(log_dir="log/{}".format(time()))
        checkpoint = ModelCheckpoint('model/cnn_model.ckpt', monitor='val_acc', verbose=1, save_best_only=True, mode='max')
        csv_logger = CSVLogger('modelEpochInfo/{0}_version_{1}.csv'.format(time(), fileCount), separator=',', append=True)
###
        def loadData():
            loadPath = 'splitData/' + dataFolder
            trainingData = np.load('./{0}/training_data.npy'.format(loadPath))
            trainingLabels = np.load('./{0}/training_labels.npy'.format(loadPath))
            validationData = np.load('./{0}/validation_data.npy'.format(loadPath))
            validationLabels = np.load('./{0}/validation_labels.npy'.format(loadPath))

            return trainingData, trainingLabels, validationData, validationLabels


        def getTrainingBatch(trainingData, trainingLabels, batchSize):
            temp = list(zip(trainingData, trainingLabels))
            random.shuffle(temp)
            data, label = zip(*temp)
            data = np.array(data)
            label = np.array(label)
            return data[:batchSize], label[:batchSize]


###
        trainingData, trainingLabels, validationData, validationLabels = loadData()

        #print('trainingdata: ', trainingData.shape)
        #print('traininglables:' ,trainingLabels.shape)
        #print('valid data: ', validationData.shape)
        #print('validationLables: ', validationLabels.shape)
        #create our training batch generator
        def generator(n):
            while True:
                batch_x,batch_y = getTrainingBatch(trainingData, trainingLabels, n)
                batch_y = to_categorical(batch_y)
                yield batch_x,batch_y

        #create our testing batch generator
        #valid_x,valid_y= batchExtraction.getTestingBatch()
        #valid_y = to_categorical(valid_y)
        def validationGenerator():
            while True:
                # valid_x, valid_y = batchExtraction.getTestingBatch(validationData, validationLabels)
                valid_x, valid_y = validationData, validationLabels
                valid_y = to_categorical(valid_y)
                yield valid_x, valid_y

        #fit the model
        print('begin training')
        model.fit_generator(generator(2000),
                epochs=3000,
                steps_per_epoch=1,
                validation_data=validationGenerator(),
                validation_steps=40,
                verbose=2,
                callbacks=[tensorboard,checkpoint,csv_logger])

    elif len(sys.argv) == 4 and sys.argv[1] == 'test':

        if os.path.exists(sys.argv[2]):
            model = keras.models.load_model(sys.argv[3])

            generate_prediction(sys.argv[2],model)
        else:
            print('ooops this file does not exists %s' % sys.argv[2])

    else:
        print('error! wrong arguments to nn.py')
        print('expecting:')
        print('python nn.py train [pca_file_name]')
        print('python nn.py test [img_path] [model_path]')


