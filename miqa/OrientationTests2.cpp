#include "itkImageFileReader.h"
#include "itkImageFileWriter.h"
#include "itkOrientImageFilter.h"

int
main(int, char* [])
{
  using SpatialOrientation = itk::SpatialOrientation::ValidCoordinateOrientationFlags;
  std::map<std::string, SpatialOrientation> m_StringToCode;

  // from https://github.com/InsightSoftwareConsortium/ITK/blob/828453d1bf61c487310d2d8c9570093e08798a40/Modules/Filtering/ImageGrid/include/itkOrientImageFilter.hxx#L35-L82
  m_StringToCode["RIP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RIP;
  m_StringToCode["LIP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LIP;
  m_StringToCode["RSP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RSP;
  m_StringToCode["LSP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LSP;
  m_StringToCode["RIA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RIA;
  m_StringToCode["LIA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LIA;
  m_StringToCode["RSA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RSA;
  m_StringToCode["LSA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LSA;
  m_StringToCode["IRP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IRP;
  m_StringToCode["ILP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ILP;
  m_StringToCode["SRP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SRP;
  m_StringToCode["SLP"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SLP;
  m_StringToCode["IRA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IRA;
  m_StringToCode["ILA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ILA;
  m_StringToCode["SRA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SRA;
  m_StringToCode["SLA"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SLA;
  m_StringToCode["RPI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RPI;
  m_StringToCode["LPI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LPI;
  m_StringToCode["RAI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RAI;
  m_StringToCode["LAI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LAI;
  m_StringToCode["RPS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RPS;
  m_StringToCode["LPS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LPS;
  m_StringToCode["RAS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_RAS;
  m_StringToCode["LAS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_LAS;
  m_StringToCode["PRI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PRI;
  m_StringToCode["PLI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PLI;
  m_StringToCode["ARI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ARI;
  m_StringToCode["ALI"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ALI;
  m_StringToCode["PRS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PRS;
  m_StringToCode["PLS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PLS;
  m_StringToCode["ARS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ARS;
  m_StringToCode["ALS"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ALS;
  m_StringToCode["IPR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IPR;
  m_StringToCode["SPR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SPR;
  m_StringToCode["IAR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IAR;
  m_StringToCode["SAR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SAR;
  m_StringToCode["IPL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IPL;
  m_StringToCode["SPL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SPL;
  m_StringToCode["IAL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_IAL;
  m_StringToCode["SAL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_SAL;
  m_StringToCode["PIR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PIR;
  m_StringToCode["PSR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PSR;
  m_StringToCode["AIR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_AIR;
  m_StringToCode["ASR"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ASR;
  m_StringToCode["PIL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PIL;
  m_StringToCode["PSL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_PSL;
  m_StringToCode["AIL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_AIL;
  m_StringToCode["ASL"] = SpatialOrientation::ITK_COORDINATE_ORIENTATION_ASL;


  std::string path = "M:/MIQA/OrientationTests2/";
  std::string inputFileName = path + "InputLPS.nrrd";

  constexpr unsigned int Dimension = 3;

  using PixelType = short;
  using ImageType = itk::Image<PixelType, Dimension>;
  using ScalarType = double;
  using IndexValueType = typename itk::Index<Dimension>::IndexValueType;

  using ReaderType = itk::ImageFileReader<ImageType>;
  typename ReaderType::Pointer reader = ReaderType::New();
  reader->SetFileName(inputFileName);
  reader->Update();

  using ReorientFilterType = itk::OrientImageFilter<ImageType, ImageType>;
  typename ReorientFilterType::Pointer reorientFilter = ReorientFilterType::New();

  reorientFilter->SetInput(reader->GetOutput());
  reorientFilter->UseImageDirectionOn();

  for (auto const& it : m_StringToCode)
  {
    std::cout << "Case " << it.first << ": " << it.second << std::endl;
    reorientFilter->SetDesiredCoordinateOrientation(it.second);

    try
    {
      reorientFilter->Update();
      std::string outputFileName = path + it.first + ".nrrd";
      itk::WriteImage(reorientFilter->GetOutput(), outputFileName, true);
    }
    catch (itk::ExceptionObject& error)
    {
      std::cerr << "Error: " << error << std::endl;
    }
  }

  return EXIT_SUCCESS;
}
